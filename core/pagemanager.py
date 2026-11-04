import uuid
import threading
from typing import List, Dict, Optional, Tuple, Any
import cv2
import numpy as np

from .enhancer import enhance_document, rotate_image
from .detector import four_point_transform, detect_document_corners, expand_quad
from .pdf_engine import render_pdf_to_images, compress_image_to_bytes

# Các khổ giấy tiêu chuẩn tại 200 DPI (Pixels)
PAGE_SIZES_PX: Dict[str, Tuple[int, int]] = {
    "A4": (1654, 2339),
    "A3": (2339, 3307),
    "A5": (1165, 1654),
    "letter": (1700, 2200),
}

# Các khổ giấy tiêu chuẩn trong PDF (Points: 1 inch = 72 pt)
PAGE_SIZES_PT: Dict[str, Tuple[float, float]] = {
    "A4": (595.28, 841.89),
    "A3": (841.89, 1190.55),
    "A5": (419.53, 595.28),
    "letter": (612.0, 792.0),
}


def detect_document_content_bbox(image: np.ndarray, padding: int = 24) -> Tuple[int, int, int, int]:
    """Tự động phát hiện vùng nội dung tài liệu để cắt bỏ lề trống trên, dưới, trái, phải."""
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    border_pixels = np.concatenate([gray[0, :], gray[-1, :], gray[:, 0], gray[:, -1]])
    bg_median = float(np.median(border_pixels))

    diff = np.abs(gray.astype(np.float32) - bg_median)
    mask = (diff > 18).astype(np.uint8)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    coords = cv2.findNonZero(closed)
    if coords is None:
        return 0, 0, w, h

    x, y, cw, ch = cv2.boundingRect(coords)

    x1 = max(0, x - padding)
    y1 = max(0, y - padding)
    x2 = min(w, x + cw + padding)
    y2 = min(h, y + ch + padding)

    return x1, y1, max(10, x2 - x1), max(10, y2 - y1)


class PageItem:
    """
    Đại diện cho một Trang tài liệu:
    - KHUNG TRANG GIẤY (Page Canvas): A4, A3, Letter, Fit to Image (Dọc hoặc Ngang).
    - ĐỐI TƯỢNG HÌNH ẢNH (Image Object): Bức hình được đặt trên trang giấy, có kích thước riêng và vị trí riêng.
    """
    def __init__(self, page_id: str, name: str, original_image: np.ndarray):
        self.id = page_id
        self.name = name
        self.original_image = original_image.copy()  # Ảnh gốc nguyên bản
        self.working_image = original_image.copy()   # Ảnh đang làm việc (sau khi crop/resize)
        self.rotation = 0                            # 0, 90, 180, 270
        self.filter_mode = "original"                # "original", "clean_bg", "sharp_text", etc.
        self.corners: Optional[List[List[float]]] = None  # 4 hoặc 6 điểm [[x, y], ...]
        self.brightness: float = 0.0                     # -1.0 .. +1.0
        self.contrast: float = 0.0                       # 0.0 .. +1.0
        self.target_width: Optional[int] = None
        self.target_height: Optional[int] = None

        # --- THIẾT LẬP KHUNG TRANG GIẤY (PAGE FRAME SETUP) ---
        # Mặc định: Khổ trang tài liệu chuẩn A4 Dọc
        self.page_size = "A4"
        self.orientation = "portrait"

        # --- THIẾT LẬP ĐỐI TƯỢNG HÌNH ẢNH TRÊN TRANG (IMAGE OBJECT) ---
        self.image_scale = 1.0                       # Tỷ lệ scale của hình (1.0 = 100% kích thước thật)
        self.image_placement = "center"              # "center", "top", "fit"

        # Caches
        self._processed_image: Optional[np.ndarray] = None
        self._thumb_bytes: Optional[bytes] = None
        self._preview_bytes: Optional[bytes] = None

    def invalidate_cache(self):
        self._processed_image = None
        self._thumb_bytes = None
        self._preview_bytes = None

    def crop_rect(self, x: int, y: int, w: int, h: int) -> bool:
        """Cắt xén hình ảnh theo hình chữ nhật (x, y, w, h)."""
        cur_h, cur_w = self.working_image.shape[:2]
        x = max(0, min(cur_w - 1, int(x)))
        y = max(0, min(cur_h - 1, int(y)))
        w = max(10, min(cur_w - x, int(w)))
        h = max(10, min(cur_h - y, int(h)))

        self.working_image = self.working_image[y:y + h, x:x + w].copy()
        self.invalidate_cache()
        return True

    def crop_margins(self, top: int = 0, bottom: int = 0, left: int = 0, right: int = 0) -> bool:
        """Cắt bỏ lề trên, dưới, trái, phải của hình ảnh."""
        cur_h, cur_w = self.working_image.shape[:2]
        top = max(0, min(cur_h - 20, int(top)))
        bottom = max(0, min(cur_h - top - 10, int(bottom)))
        left = max(0, min(cur_w - 20, int(left)))
        right = max(0, min(cur_w - left - 10, int(right)))

        y1 = top
        y2 = cur_h - bottom
        x1 = left
        x2 = cur_w - right

        if x2 > x1 and y2 > y1:
            self.working_image = self.working_image[y1:y2, x1:x2].copy()
            self.invalidate_cache()
            return True
        return False

    def resize_image(self, target_w: int, target_h: Optional[int] = None, fit_mode: str = "exact") -> bool:
        """Thay đổi kích thước của đối tượng hình ảnh (Scale/Resize Image Object)."""
        cur_h, cur_w = self.working_image.shape[:2]
        target_w = max(10, min(10000, int(target_w)))

        if not target_h or target_h <= 0 or fit_mode == "proportional_w":
            scale = float(target_w) / float(cur_w)
            target_h = max(10, int(round(cur_h * scale)))
        else:
            target_h = max(10, min(10000, int(target_h)))

        interp = cv2.INTER_AREA if (target_w < cur_w or target_h < cur_h) else cv2.INTER_LANCZOS4
        self.working_image = cv2.resize(self.working_image, (target_w, target_h), interpolation=interp)
        self.image_scale = 1.0  # Reset scale factor về 1.0 vì kích thước pixel đã đổi trực tiếp
        self.invalidate_cache()
        return True

    def scale_image_percent(self, percent: float) -> bool:
        """Thu phóng đối tượng hình ảnh theo %."""
        ratio = max(0.1, min(3.0, float(percent) / 100.0))
        self.image_scale = ratio
        self.invalidate_cache()
        return True

    def setup_page_canvas(
        self,
        page_size: Optional[str] = None,
        orientation: Optional[str] = None,
        placement: Optional[str] = None,
        scale: Optional[float] = None
    ):
        """Thiết lập khung trang giấy và vị trí hình ảnh trên trang."""
        if page_size is not None:
            self.page_size = page_size
        if orientation is not None:
            self.orientation = orientation
        if placement is not None:
            self.image_placement = placement
        if scale is not None:
            self.image_scale = max(0.1, min(3.0, float(scale)))
        self.invalidate_cache()

    def auto_trim(self, padding: int = 24) -> Tuple[int, int, int, int]:
        """Tự động cắt lề trống xung quanh nội dung hình ảnh."""
        x, y, w, h = detect_document_content_bbox(self.working_image, padding=padding)
        self.crop_rect(x, y, w, h)
        return x, y, w, h

    def apply_full_edit(
        self,
        corners: Optional[List[List[float]]] = None,
        rotation: Optional[int] = None,
        brightness: Optional[float] = None,
        contrast: Optional[float] = None,
        filter_mode: Optional[str] = None,
        target_w: Optional[int] = None,
        target_h: Optional[int] = None,
        image_scale: Optional[float] = None,
    ) -> bool:
        """
        Dựng lại ảnh làm việc (working_image) xác định từ ảnh gốc:
        1. Nắn phối cảnh / cắt 4 góc hoặc 6 điểm gáy sách (nếu có corners)
        2. Xoay góc (nếu có rotation)
        3. Tăng cường màu sắc, độ sáng & độ tương phản
        4. Co giãn kích thước mục tiêu (nếu có target_w, target_h)
        """
        if corners is not None:
            self.corners = corners if (isinstance(corners, (list, tuple)) and len(corners) in (4, 6)) else None
        if rotation is not None:
            self.rotation = int(rotation) % 360
        if brightness is not None:
            self.brightness = max(-1.0, min(1.0, float(brightness)))
        if contrast is not None:
            self.contrast = max(0.0, min(1.0, float(contrast)))
        if filter_mode is not None:
            self.filter_mode = filter_mode
        if target_w is not None and target_w > 0:
            self.target_width = int(target_w)
        if target_h is not None and target_h > 0:
            self.target_height = int(target_h)

        if self.target_width and self.target_height:
            self.image_scale = 1.0  # Đã resize kích thước pixel cụ thể thì image_scale luôn là 1.0 (100%), không nhân đôi
        elif image_scale is not None:
            self.image_scale = max(0.1, min(3.0, float(image_scale)))

        # 1. Ảnh cơ sở: nắn theo corners (4 hoặc 6 điểm)
        if self.corners and len(self.corners) in (4, 6):
            work = four_point_transform(self.original_image, np.array(self.corners, dtype=np.float32))
        else:
            work = self.original_image.copy()

        # 2. Xoay góc
        if self.rotation % 360 != 0:
            work = rotate_image(work, self.rotation)

        # 3. Lọc màu & sáng tối
        work = enhance_document(
            work,
            mode=self.filter_mode or "original",
            contrast=self.contrast,
            brightness=self.brightness,
        )

        # 4. Kích thước W x H
        if self.target_width and self.target_height:
            interp = cv2.INTER_AREA if (self.target_width < work.shape[1] or self.target_height < work.shape[0]) else cv2.INTER_LANCZOS4
            work = cv2.resize(work, (self.target_width, self.target_height), interpolation=interp)

        self.working_image = work
        self.invalidate_cache()
        return True

    def reset_to_original(self):
        """Khôi phục lại hình ảnh nguyên bản như lúc mới tải lên."""
        self.corners = None
        self.rotation = 0
        self.brightness = 0.0
        self.contrast = 0.0
        self.filter_mode = "original"
        self.target_width = None
        self.target_height = None
        self.image_scale = 1.0
        self.page_size = "fit_image"
        self.image_placement = "center"
        self.working_image = self.original_image.copy()
        self.invalidate_cache()

    def get_raw_processed_image(self) -> np.ndarray:
        """Lấy hình ảnh thuần (đã qua xử lý, chưa ghép vào khung giấy)."""
        return self.working_image

    def get_processed_image(self) -> np.ndarray:
        """
        KẾT XUẤT TRANG TÀI LIỆU HOÀN CHỈNH:
        Ghép đối tượng hình ảnh (Image Object) lên Khung trang giấy (Page Canvas).
        """
        if self._processed_image is not None:
            return self._processed_image

        raw_img = self.get_raw_processed_image()
        ih, iw = raw_img.shape[:2]

        # 1. Nếu khổ trang là "fit_image": Trang lấy đúng kích thước thật của hình ảnh
        if self.page_size == "fit_image":
            if abs(self.image_scale - 1.0) > 0.01:
                nw = max(10, int(round(iw * self.image_scale)))
                nh = max(10, int(round(ih * self.image_scale)))
                interp = cv2.INTER_AREA if self.image_scale < 1.0 else cv2.INTER_LANCZOS4
                self._processed_image = cv2.resize(raw_img, (nw, nh), interpolation=interp)
            else:
                self._processed_image = raw_img
            return self._processed_image

        # 2. Khổ trang chuẩn giấy (A4, A3, A5, Letter)
        base_w, base_h = PAGE_SIZES_PX.get(self.page_size, PAGE_SIZES_PX["A4"])
        if self.orientation == "landscape":
            canvas_w, canvas_h = max(base_w, base_h), min(base_w, base_h)
        else:
            canvas_w, canvas_h = min(base_w, base_h), max(base_w, base_h)

        # Tạo tờ giấy nền trắng tinh
        canvas = np.full((canvas_h, canvas_w, 3), 255, dtype=np.uint8)

        # Kích thước thật của hình ảnh theo tỷ lệ scale của người dùng (1.0 = 100% kích thước thật)
        # KHÔNG tự động co dãn hay ép fill trang!
        target_w = max(10, int(round(iw * self.image_scale)))
        target_h = max(10, int(round(ih * self.image_scale)))

        if abs(self.image_scale - 1.0) > 0.01:
            interp = cv2.INTER_AREA if self.image_scale < 1.0 else cv2.INTER_LANCZOS4
            placed_img = cv2.resize(raw_img, (target_w, target_h), interpolation=interp)
        else:
            placed_img = raw_img

        # Vị trí đặt hình ảnh trên tờ giấy:
        # - Mặc định căn giữa: nếu hình nhỏ hơn giấy thì lọt gọn bên trong, nếu to hơn thì tràn mép và bị cắt
        pos_x = (canvas_w - target_w) // 2
        if self.image_placement == "top":
            pos_y = max(40, int(canvas_h * 0.06))
        elif self.image_placement == "bottom":
            pos_y = max(40, canvas_h - target_h - 40)
        else:
            pos_y = (canvas_h - target_h) // 2

        # Tính toán vùng giao giữa placed_img và canvas (tự động cắt bỏ phần tràn mép)
        src_x1 = max(0, -pos_x)
        src_y1 = max(0, -pos_y)
        dst_x1 = max(0, pos_x)
        dst_y1 = max(0, pos_y)

        src_x2 = min(target_w, canvas_w - pos_x)
        src_y2 = min(target_h, canvas_h - pos_y)
        dst_x2 = dst_x1 + (src_x2 - src_x1)
        dst_y2 = dst_y1 + (src_y2 - src_y1)

        if (src_x2 > src_x1) and (src_y2 > src_y1):
            canvas[dst_y1:dst_y2, dst_x1:dst_x2] = placed_img[src_y1:src_y2, src_x1:src_x2]

        self._processed_image = canvas
        return self._processed_image

    def get_thumbnail(self, max_dim: int = 360) -> bytes:
        if self._thumb_bytes is not None:
            return self._thumb_bytes

        img = self.get_processed_image()
        h, w = img.shape[:2]
        longest = max(h, w)
        if longest > max_dim:
            scale = float(max_dim) / float(longest)
            nw = max(1, int(round(w * scale)))
            nh = max(1, int(round(h * scale)))
            thumb = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
        else:
            thumb = img

        ok, buf = cv2.imencode(".jpg", thumb, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        self._thumb_bytes = buf.tobytes() if ok else b""
        return self._thumb_bytes

    def get_preview(self, max_dim: int = 1600) -> bytes:
        if self._preview_bytes is not None:
            return self._preview_bytes

        img = self.get_processed_image()
        h, w = img.shape[:2]
        longest = max(h, w)
        if longest > max_dim:
            scale = float(max_dim) / float(longest)
            nw = max(1, int(round(w * scale)))
            nh = max(1, int(round(h * scale)))
            preview = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
        else:
            preview = img

        ok, buf = cv2.imencode(".jpg", preview, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        self._preview_bytes = buf.tobytes() if ok else b""
        return self._preview_bytes

    def to_dict(self, index: int) -> Dict[str, Any]:
        canvas = self.get_processed_image()
        ch, cw = canvas.shape[:2]

        raw = self.get_raw_processed_image()
        ih, iw = raw.shape[:2]
        orig_h, orig_w = self.original_image.shape[:2]

        is_modified = (
            self.corners is not None or
            self.rotation != 0 or
            self.filter_mode != "original" or
            abs(self.brightness) > 0.01 or
            self.contrast > 0.01 or
            iw != orig_w or ih != orig_h or
            self.page_size != "A4" or
            abs(self.image_scale - 1.0) > 0.01
        )

        return {
            "id": self.id,
            "order": index + 1,
            "name": self.name,
            # Kích thước khung trang giấy (Canvas/Paper)
            "width": cw,
            "height": ch,
            # Kích thước đối tượng hình ảnh thật
            "image_width": iw,
            "image_height": ih,
            "orig_width": orig_w,
            "orig_height": orig_h,
            # Thiết lập khung trang và vị trí
            "page_size": self.page_size,
            "orientation": self.orientation,
            "image_placement": self.image_placement,
            "image_scale": round(self.image_scale, 2),
            "image_scale_pct": int(round(self.image_scale * 100)),
            # Chỉnh sửa ảnh cốt lõi
            "corners": self.corners,
            "brightness": round(self.brightness, 2),
            "contrast": round(self.contrast, 2),
            # Trạng thái
            "is_modified": is_modified,
            "rotation": self.rotation,
            "filter_mode": self.filter_mode,
        }


class PageManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._pages: List[PageItem] = []
        # Khổ trang tài liệu áp dụng TOÀN CỤC cho toàn file (Mặc định chuẩn văn phòng: A4 Dọc)
        self.doc_page_size: str = "A4"
        self.doc_orientation: str = "portrait"

    def set_document_page_size(self, page_size: str = "fit_image", orientation: str = "portrait") -> int:
        """Thiết lập khổ trang đồng nhất cho TOÀN BỘ file tài liệu (Document Page Size)."""
        with self._lock:
            self.doc_page_size = page_size
            self.doc_orientation = orientation
            for p in self._pages:
                p.page_size = page_size
                p.orientation = orientation
                p.invalidate_cache()
            return len(self._pages)

    def add_image(self, name: str, img_bgr: np.ndarray) -> PageItem:
        with self._lock:
            page_id = uuid.uuid4().hex[:12]
            item = PageItem(page_id, name, img_bgr)
            item.page_size = self.doc_page_size
            item.orientation = self.doc_orientation
            self._pages.append(item)
            return item

    def add_pdf(self, name: str, pdf_bytes: bytes, dpi: float = 200.0) -> List[PageItem]:
        rendered = render_pdf_to_images(pdf_bytes, dpi=dpi)
        created_items = []
        with self._lock:
            for idx, (bgr, label) in enumerate(rendered):
                page_id = uuid.uuid4().hex[:12]
                item_name = f"{name} ({label})" if len(rendered) > 1 else name
                item = PageItem(page_id, item_name, bgr)
                item.page_size = self.doc_page_size
                item.orientation = self.doc_orientation
                self._pages.append(item)
                created_items.append(item)
        return created_items

    def list_pages(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [page.to_dict(idx) for idx, page in enumerate(self._pages)]

    def get_distinct_dimensions(self) -> List[Dict[str, Any]]:
        """Lấy danh sách các kích thước khác nhau hiện có giữa các trang."""
        with self._lock:
            dim_map: Dict[Tuple[int, int], List[str]] = {}
            for idx, p in enumerate(self._pages):
                raw = p.get_raw_processed_image()
                h, w = raw.shape[:2]
                key = (w, h)
                if key not in dim_map:
                    dim_map[key] = []
                dim_map[key].append(f"Trang {idx + 1}")

            result = []
            for (w, h), page_names in sorted(dim_map.items(), key=lambda item: len(item[1]), reverse=True):
                result.append({
                    "width": w,
                    "height": h,
                    "count": len(page_names),
                    "label": f"{w} × {h} px ({len(page_names)} trang)",
                    "pages": page_names,
                })
            return result

    def get_page(self, page_id: str) -> Optional[PageItem]:
        with self._lock:
            for p in self._pages:
                if p.id == page_id:
                    return p
            return None

    def setup_pages(
        self,
        page_ids: Optional[List[str]] = None,
        page_size: Optional[str] = None,
        orientation: Optional[str] = None,
        placement: Optional[str] = None,
        scale: Optional[float] = None
    ) -> int:
        """Thiết lập Khung trang giấy (A4, A3...) và vị trí cho 1 hoặc nhiều trang."""
        with self._lock:
            targets = set(page_ids) if page_ids else {p.id for p in self._pages}
            count = 0
            for p in self._pages:
                if p.id in targets:
                    p.setup_page_canvas(
                        page_size=page_size,
                        orientation=orientation,
                        placement=placement,
                        scale=scale
                    )
                    count += 1
            return count

    def resize_page_image(
        self,
        page_id: str,
        target_w: int,
        target_h: Optional[int] = None,
        fit_mode: str = "exact",
    ) -> bool:
        """Thay đổi kích thước của đối tượng hình ảnh (Image Object)."""
        with self._lock:
            page = self.get_page(page_id)
            if page:
                return page.resize_image(target_w, target_h, fit_mode=fit_mode)
            return False

    def resize_multiple_page_images(
        self,
        page_ids: List[str],
        target_w: int,
        target_h: Optional[int] = None,
        fit_mode: str = "exact",
    ) -> int:
        with self._lock:
            targets = set(page_ids) if page_ids else {p.id for p in self._pages}
            count = 0
            for p in self._pages:
                if p.id in targets:
                    if p.resize_image(target_w, target_h, fit_mode=fit_mode):
                        count += 1
            return count

    def resize_page(
        self,
        page_id: str,
        target_w: int,
        target_h: Optional[int] = None,
        fit_mode: str = "exact",
    ) -> bool:
        return self.resize_page_image(page_id, target_w, target_h, fit_mode)

    def resize_multiple_pages(
        self,
        page_ids: List[str],
        target_w: int,
        target_h: Optional[int] = None,
        fit_mode: str = "exact",
    ) -> int:
        return self.resize_multiple_page_images(page_ids, target_w, target_h, fit_mode)

    def scale_page(self, page_id: str, percent: float) -> bool:
        return self.scale_page_image(page_id, percent)

    def crop_page_rect(self, page_id: str, x: int, y: int, w: int, h: int) -> bool:
        with self._lock:
            page = self.get_page(page_id)
            if page:
                return page.crop_rect(x, y, w, h)
            return False

    def crop_page_margins(self, page_id: str, top: int, bottom: int, left: int, right: int) -> bool:
        with self._lock:
            page = self.get_page(page_id)
            if page:
                return page.crop_margins(top, bottom, left, right)
            return False

    def auto_trim_page(self, page_id: str, padding: int = 24) -> Optional[Tuple[int, int, int, int]]:
        with self._lock:
            page = self.get_page(page_id)
            if page:
                return page.auto_trim(padding=padding)
            return None

    def reset_page(self, page_id: str) -> bool:
        with self._lock:
            page = self.get_page(page_id)
            if page:
                page.reset_to_original()
                return True
            return False

    def reorder(self, page_ids: List[str]) -> bool:
        with self._lock:
            id_map = {p.id: p for p in self._pages}
            new_list = []
            for pid in page_ids:
                if pid in id_map:
                    new_list.append(id_map.pop(pid))
            for remaining in self._pages:
                if remaining.id in id_map:
                    new_list.append(remaining)
            self._pages = new_list
            return True

    def rotate_pages(self, page_ids: List[str], angle_delta: int = 90) -> bool:
        with self._lock:
            targets = set(page_ids) if page_ids else {p.id for p in self._pages}
            for p in self._pages:
                if p.id in targets:
                    new_rot = (p.rotation + angle_delta) % 360
                    p.apply_full_edit(rotation=new_rot)
            return True

    def set_filter(self, page_ids: List[str], filter_mode: str) -> bool:
        with self._lock:
            targets = set(page_ids) if page_ids else {p.id for p in self._pages}
            for p in self._pages:
                if p.id in targets:
                    p.apply_full_edit(filter_mode=filter_mode)
            return True

    def delete_pages(self, page_ids: List[str]) -> int:
        with self._lock:
            targets = set(page_ids)
            initial_count = len(self._pages)
            self._pages = [p for p in self._pages if p.id not in targets]
            return initial_count - len(self._pages)

    def duplicate_page(self, page_id: str) -> Optional[PageItem]:
        with self._lock:
            idx = -1
            target_page = None
            for i, p in enumerate(self._pages):
                if p.id == page_id:
                    idx = i
                    target_page = p
                    break

            if target_page is None:
                return None

            new_id = uuid.uuid4().hex[:12]
            new_item = PageItem(new_id, f"{target_page.name} (Bản sao)", target_page.working_image.copy())
            new_item.rotation = target_page.rotation
            new_item.filter_mode = target_page.filter_mode
            new_item.page_size = target_page.page_size
            new_item.orientation = target_page.orientation
            new_item.image_placement = target_page.image_placement
            new_item.image_scale = target_page.image_scale
            self._pages.insert(idx + 1, new_item)
            return new_item

    def clear(self):
        with self._lock:
            self._pages.clear()

    def get_ordered_processed_images(self, page_ids: Optional[List[str]] = None) -> List[np.ndarray]:
        with self._lock:
            if page_ids:
                id_map = {p.id: p for p in self._pages}
                pages_to_process = [id_map[pid] for pid in page_ids if pid in id_map]
            else:
                pages_to_process = list(self._pages)

        return [p.get_processed_image() for p in pages_to_process]

    def get_ordered_pages(self, page_ids: Optional[List[str]] = None) -> List[PageItem]:
        with self._lock:
            if page_ids:
                id_map = {p.id: p for p in self._pages}
                return [id_map[pid] for pid in page_ids if pid in id_map]
            return list(self._pages)
