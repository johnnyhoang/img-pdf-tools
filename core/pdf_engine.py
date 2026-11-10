import io
from typing import List, Tuple, Optional, Dict, Any, Union
import cv2
import numpy as np
from PIL import Image
import fitz  # PyMuPDF


# Các khổ giấy tiêu chuẩn trong PDF (Points: 1 inch = 72 pt)
PAGE_SIZES_PT: Dict[str, Tuple[float, float]] = {
    "A4": (595.28, 841.89),
    "a4": (595.28, 841.89),
    "A3": (841.89, 1190.55),
    "a3": (841.89, 1190.55),
    "A5": (419.53, 595.28),
    "a5": (419.53, 595.28),
    "letter": (612.0, 792.0),
    "Letter": (612.0, 792.0),
}


def format_file_size(size_bytes: int) -> str:
    """Định dạng byte sang chuỗi thân thiện với người dùng (KB, MB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def render_pdf_to_images(
    pdf_bytes: bytes,
    dpi: float = 200.0,
    max_dim_per_page: int = 2400
) -> List[Tuple[np.ndarray, str]]:
    """
    Trích xuất toàn bộ các trang của file PDF thành danh sách ảnh NumPy BGR và tên trang.
    Sử dụng PyMuPDF (fitz) kết xuất độ nét cao theo DPI chỉ định.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError("Tệp PDF bị lỗi hoặc không thể đọc.")

    if doc.is_encrypted:
        raise ValueError("Tệp PDF được cài mật khẩu bảo vệ. Vui lòng mở khóa trước.")

    if len(doc) == 0:
        raise ValueError("Tệp PDF rỗng, không chứa trang nào.")

    results: List[Tuple[np.ndarray, str]] = []
    total_pages = len(doc)

    for page_idx in range(total_pages):
        page = doc[page_idx]
        rect = page.rect
        w_pt, h_pt = float(rect.width), float(rect.height)
        if w_pt <= 0 or h_pt <= 0:
            continue

        scale = min(dpi / 72.0, float(max_dim_per_page) / max(w_pt, h_pt))
        scale = max(scale, 100.0 / 72.0)  # Tối thiểu ~100 DPI để rõ chữ

        matrix = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        samples = np.frombuffer(pix.samples, dtype=np.uint8)
        img = samples.reshape((pix.height, pix.width, pix.n))

        if pix.n == 3:
            bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        elif pix.n == 1:
            bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif pix.n == 4:
            bgr = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        else:
            bgr = cv2.cvtColor(img[:, :, :3], cv2.COLOR_RGB2BGR)

        page_label = f"Trang {page_idx + 1}"
        results.append((bgr, page_label))

    doc.close()
    if not results:
        raise ValueError("Không thể trích xuất trang nào từ tệp PDF.")

    return results


def compress_image_to_bytes(
    image: np.ndarray,
    format: str = "JPEG",
    quality: int = 85,
    max_long_edge: Optional[int] = None
) -> Tuple[bytes, str]:
    """Nén ảnh OpenCV BGR thành bytes tối ưu theo chất lượng và giới hạn cạnh dài."""
    h, w = image.shape[:2]
    if max_long_edge and max_long_edge > 0 and max(h, w) > max_long_edge:
        scale = float(max_long_edge) / float(max(h, w))
        nw = max(1, int(round(w * scale)))
        nh = max(1, int(round(h * scale)))
        proc = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_AREA)
    else:
        proc = image

    fmt = (format or "JPEG").upper()
    quality = max(10, min(100, int(quality or 85)))

    if fmt in ["JPG", "JPEG"]:
        ok, buf = cv2.imencode(".jpg", proc, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        return buf.tobytes(), "image/jpeg"
    elif fmt == "PNG":
        compression = max(1, min(9, int((100 - quality) / 10)))
        ok, buf = cv2.imencode(".png", proc, [int(cv2.IMWRITE_PNG_COMPRESSION), compression])
        return buf.tobytes(), "image/png"
    elif fmt == "WEBP":
        ok, buf = cv2.imencode(".webp", proc, [int(cv2.IMWRITE_WEBP_QUALITY), quality])
        return buf.tobytes(), "image/webp"
    else:
        ok, buf = cv2.imencode(".jpg", proc, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        return buf.tobytes(), "image/jpeg"


def estimate_images_size(
    images: List[np.ndarray],
    format: str = "JPEG",
    quality: int = 85,
    max_long_edge: Optional[int] = None
) -> Dict[str, Any]:
    """
    Ước lượng kích thước và dung lượng nén của danh sách ảnh.
    Tính toán nhanh trên mẫu đại diện hoặc toàn bộ trang.
    """
    if not images:
        return {
            "total_bytes": 0,
            "formatted_total": "0 B",
            "avg_bytes": 0,
            "formatted_avg": "0 B",
            "sample_width": 0,
            "sample_height": 0,
            "count": 0,
        }

    total_count = len(images)
    sample_indices = np.linspace(0, total_count - 1, min(5, total_count), dtype=int)
    sample_bytes_list = []
    sample_w, sample_h = 0, 0

    for idx in sample_indices:
        img = images[idx]
        b_data, _ = compress_image_to_bytes(img, format=format, quality=quality, max_long_edge=max_long_edge)
        sample_bytes_list.append(len(b_data))
        if sample_w == 0:
            h, w = img.shape[:2]
            if max_long_edge and max_long_edge > 0 and max(h, w) > max_long_edge:
                scale = float(max_long_edge) / float(max(h, w))
                sample_w = int(round(w * scale))
                sample_h = int(round(h * scale))
            else:
                sample_w = w
                sample_h = h

    avg_bytes = int(sum(sample_bytes_list) / len(sample_bytes_list))
    total_estimated_bytes = avg_bytes * total_count

    return {
        "total_bytes": total_estimated_bytes,
        "formatted_total": format_file_size(total_estimated_bytes),
        "avg_bytes": avg_bytes,
        "formatted_avg": format_file_size(avg_bytes),
        "sample_width": sample_w,
        "sample_height": sample_h,
        "count": total_count,
    }


def build_pdf_from_pages(
    pages: List[Any],
    layout_mode: Optional[str] = None,
    quality: int = 85,
    normalize_res: bool = True
) -> bytes:
    """
    Tạo tệp PDF đa trang theo mô hình chuẩn Document App:
    - KHUNG TRANG GIẤY (Page Canvas): A4, A3, Letter, Fit to image.
    - ĐỐI TƯỢNG HÌNH ẢNH (Image Object): Đặt lên trang giấy theo kích thước scale và vị trí căn chỉnh.
    """
    if not pages:
        raise ValueError("Không có trang nào để tạo PDF.")

    pdf_doc = fitz.open()
    DPI = 200.0
    pt_per_px = 72.0 / DPI

    for p in pages:
        # Nếu truyền trực tiếp numpy array (tương thích ngược)
        if isinstance(p, np.ndarray):
            raw_img = p
            p_size = "fit_image" if layout_mode == "original" else "A4"
            p_orient = "portrait"
            p_placement = "center"
            p_scale = 1.0
        else:
            raw_img = p.get_raw_processed_image()
            p_size = getattr(p, "page_size", "A4")
            p_orient = getattr(p, "orientation", "portrait")
            p_placement = getattr(p, "image_placement", "center")
            p_scale = getattr(p, "image_scale", 1.0)

        # Ghi đè layout_mode nếu người dùng chọn ghi đè toàn bộ tài liệu
        if layout_mode == "original":
            p_size = "fit_image"
        elif layout_mode == "uniform_a4_portrait":
            p_size = "A4"
            p_orient = "portrait"
        elif layout_mode == "uniform_a4_landscape":
            p_size = "A4"
            p_orient = "landscape"
        elif layout_mode in ("uniform_letter_portrait", "letter_portrait"):
            p_size = "letter"
            p_orient = "portrait"
        elif layout_mode in ("uniform_letter_landscape", "letter_landscape"):
            p_size = "letter"
            p_orient = "landscape"

        ih, iw = raw_img.shape[:2]
        target_edge = 2400 if normalize_res and max(ih, iw) > 3600 else None
        img_bytes, _ = compress_image_to_bytes(raw_img, format="JPEG", quality=quality, max_long_edge=target_edge)

        # 1. Trường hợp Khung trang vừa khít ảnh (Fit to Image)
        if p_size == "fit_image":
            pw_pt = float(iw) * pt_per_px * p_scale
            ph_pt = float(ih) * pt_per_px * p_scale
            page = pdf_doc.new_page(width=pw_pt, height=ph_pt)
            page.insert_image(fitz.Rect(0, 0, pw_pt, ph_pt), stream=img_bytes)
            continue

        # 2. Trường hợp Khung trang giấy chuẩn (A4, A3, Letter...)
        base_size = PAGE_SIZES_PT.get(p_size) or PAGE_SIZES_PT.get(str(p_size).lower()) or PAGE_SIZES_PT.get(str(p_size).upper()) or PAGE_SIZES_PT["A4"]
        base_w_pt, base_h_pt = base_size
        if p_orient == "landscape":
            pw_pt, ph_pt = max(base_w_pt, base_h_pt), min(base_w_pt, base_h_pt)
        else:
            pw_pt, ph_pt = min(base_w_pt, base_h_pt), max(base_w_pt, base_h_pt)

        # Kích thước đặt hình ảnh trên trang PDF:
        if p_placement == "fill":
            # Phóng to lấp đầy tràn toàn bộ trang PDF (không viền trắng, cắt lẹm mép thừa)
            fill_scale = max(pw_pt / float(iw), ph_pt / float(ih)) * p_scale
            fit_w = float(iw) * fill_scale
            fit_h = float(ih) * fill_scale
        elif p_placement == "fit":
            # Co vừa vặn toàn bộ ảnh vào trong trang PDF
            fit_scale = min(pw_pt / float(iw), ph_pt / float(ih)) * p_scale
            fit_w = float(iw) * fit_scale
            fit_h = float(ih) * fit_scale
        else:
            # Kích thước thật theo tỷ lệ scale của người dùng (1.0 = 100%)
            fit_w = float(iw) * pt_per_px * p_scale
            fit_h = float(ih) * pt_per_px * p_scale

        offset_x = (pw_pt - fit_w) / 2.0
        if p_placement == "top":
            offset_y = max(20.0, ph_pt * 0.06)
        elif p_placement == "bottom":
            offset_y = max(20.0, ph_pt - fit_h - 20.0)
        else:
            offset_y = (ph_pt - fit_h) / 2.0

        page = pdf_doc.new_page(width=pw_pt, height=ph_pt)
        rect = fitz.Rect(offset_x, offset_y, offset_x + fit_w, offset_y + fit_h)
        page.insert_image(rect, stream=img_bytes, keep_proportion=True)

    pdf_bytes = pdf_doc.write(deflate=True, garbage=3)
    pdf_doc.close()
    return pdf_bytes


def build_pdf_from_images(
    images: List[np.ndarray],
    layout_mode: str = "original",
    quality: int = 85,
    normalize_res: bool = True
) -> bytes:
    """Wrapper tương thích ngược nhận danh sách numpy array."""
    return build_pdf_from_pages(images, layout_mode=layout_mode, quality=quality, normalize_res=normalize_res)


def estimate_pdf_size(
    images: List[np.ndarray],
    layout_mode: str = "original",
    quality: int = 85
) -> Dict[str, Any]:
    """Ước lượng nhanh dung lượng tệp PDF xuất ra."""
    if not images:
        return {"total_bytes": 0, "formatted_total": "0 B"}

    sample_size = min(3, len(images))
    sample_pdf = build_pdf_from_images(images[:sample_size], layout_mode=layout_mode, quality=quality)
    avg_per_page = len(sample_pdf) / float(sample_size)
    total_est = int(avg_per_page * len(images))

    return {
        "total_bytes": total_est,
        "formatted_total": format_file_size(total_est),
        "count": len(images),
    }
