import io
import math
from typing import List, Tuple, Optional, Dict, Any

import cv2
import numpy as np


def parse_color_hex(hex_str: str, default: Tuple[int, int, int] = (255, 255, 255)) -> Tuple[int, int, int]:
    """Chuyển đổi mã màu hex (#ffffff hoặc #0f172a) sang BGR tuple cho OpenCV."""
    if not hex_str or not isinstance(hex_str, str):
        return default
    h = hex_str.strip().lstrip("#")
    if len(h) == 3:
        h = "".join([c * 2 for c in h])
    if len(h) == 6:
        try:
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            return (b, g, r)  # BGR
        except ValueError:
            pass
    return default


def stitch_images(
    images: List[np.ndarray],
    layout: str = "grid",
    cols: int = 3,
    spacing: int = 24,
    padding: int = 32,
    bg_color: Tuple[int, int, int] = (255, 255, 255),
    draw_border: bool = True,
    last_row_align: str = "center",
    scale: float = 1.0,
    max_total_dim: int = 24000
) -> np.ndarray:
    """
    Ghép danh sách ảnh thành 1 ảnh tổng hợp duy nhất.

    Bố cục:
      - "vertical": Xếp thành 1 dải ảnh dài dọc.
      - "grid": Xếp thành lưới N cột (căn giữa hoặc căn trái hàng cuối).
      - "horizontal": Xếp thành 1 hàng ngang.
    """
    if not images:
        raise ValueError("Danh sách ảnh rỗng, không có trang nào để ghép.")

    # 1. Thu phóng ảnh theo tỷ lệ scale
    processed_images: List[np.ndarray] = []
    scale = max(0.1, min(2.0, float(scale or 1.0)))
    for img in images:
        h, w = img.shape[:2]
        if abs(scale - 1.0) > 0.01:
            nw = max(10, int(round(w * scale)))
            nh = max(10, int(round(h * scale)))
            resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LANCZOS4)
            processed_images.append(resized)
        else:
            processed_images.append(img)

    num_pages = len(processed_images)
    spacing = max(0, int(spacing))
    padding = max(0, int(padding))

    # 2. Xử lý ghép theo bố cục
    if layout == "vertical" or cols <= 1:
        # BỐ CỤC DỌC (1 CỘT DÀI)
        max_w = max(img.shape[1] for img in processed_images)
        total_w = max_w + 2 * padding
        total_h = sum(img.shape[0] for img in processed_images) + (num_pages - 1) * spacing + 2 * padding

        canvas = np.full((total_h, total_w, 3), bg_color, dtype=np.uint8)

        cur_y = padding
        for img in processed_images:
            h, w = img.shape[:2]
            cur_x = padding + (max_w - w) // 2
            canvas[cur_y:cur_y + h, cur_x:cur_x + w] = img
            if draw_border:
                cv2.rectangle(canvas, (cur_x, cur_y), (cur_x + w - 1, cur_y + h - 1), (218, 222, 229), 1)
            cur_y += h + spacing

    elif layout == "horizontal":
        # BỐ CỤC NGANG (1 HÀNG)
        max_h = max(img.shape[0] for img in processed_images)
        total_h = max_h + 2 * padding
        total_w = sum(img.shape[1] for img in processed_images) + (num_pages - 1) * spacing + 2 * padding

        canvas = np.full((total_h, total_w, 3), bg_color, dtype=np.uint8)

        cur_x = padding
        for img in processed_images:
            h, w = img.shape[:2]
            cur_y = padding + (max_h - h) // 2
            canvas[cur_y:cur_y + h, cur_x:cur_x + w] = img
            if draw_border:
                cv2.rectangle(canvas, (cur_x, cur_y), (cur_x + w - 1, cur_y + h - 1), (218, 222, 229), 1)
            cur_x += w + spacing

    else:
        # BỐ CỤC LƯỚI (GRID N CỘT)
        cols = max(1, int(cols))
        cols = min(cols, num_pages)

        # Chuẩn hóa độ rộng cột: lấy độ rộng tối đa của các trang
        col_w = max(img.shape[1] for img in processed_images)

        scaled_grid_imgs: List[np.ndarray] = []
        for img in processed_images:
            h, w = img.shape[:2]
            if w != col_w:
                ratio = float(col_w) / float(w)
                new_h = max(10, int(round(h * ratio)))
                resized = cv2.resize(img, (col_w, new_h), interpolation=cv2.INTER_AREA if ratio < 1.0 else cv2.INTER_LANCZOS4)
                scaled_grid_imgs.append(resized)
            else:
                scaled_grid_imgs.append(img)

        rows_data = []
        for i in range(0, num_pages, cols):
            row_items = scaled_grid_imgs[i:i + cols]
            row_max_h = max(item.shape[0] for item in row_items)
            rows_data.append((row_items, row_max_h))

        grid_content_w = cols * col_w + (cols - 1) * spacing
        total_w = grid_content_w + 2 * padding
        total_h = sum(r_h for _, r_h in rows_data) + (len(rows_data) - 1) * spacing + 2 * padding

        canvas = np.full((total_h, total_w, 3), bg_color, dtype=np.uint8)

        cur_y = padding
        for row_items, row_h in rows_data:
            item_count = len(row_items)
            if item_count < cols and last_row_align == "center":
                row_content_w = item_count * col_w + (item_count - 1) * spacing
                start_x = padding + (grid_content_w - row_content_w) // 2
            else:
                start_x = padding

            for idx, img in enumerate(row_items):
                ih, iw = img.shape[:2]
                ix = start_x + idx * (col_w + spacing)
                iy = cur_y + (row_h - ih) // 2

                canvas[iy:iy + ih, ix:ix + iw] = img
                if draw_border:
                    cv2.rectangle(canvas, (ix, iy), (ix + iw - 1, iy + ih - 1), (218, 222, 229), 1)

            cur_y += row_h + spacing

    # 3. Giới hạn kích thước tối đa chống tràn RAM
    ch, cw = canvas.shape[:2]
    longest = max(ch, cw)
    if longest > max_total_dim:
        scale_down = float(max_total_dim) / float(longest)
        target_w = max(10, int(round(cw * scale_down)))
        target_h = max(10, int(round(ch * scale_down)))
        canvas = cv2.resize(canvas, (target_w, target_h), interpolation=cv2.INTER_AREA)

    return canvas


def encode_stitched_image(
    image: np.ndarray,
    format: str = "jpeg",
    quality: int = 90
) -> Tuple[bytes, str]:
    """Mã hóa ảnh ghép thành bytes JPEG hoặc PNG."""
    fmt = (format or "jpeg").lower()
    if fmt in ("png",):
        ok, buf = cv2.imencode(".png", image, [int(cv2.IMWRITE_PNG_COMPRESSION), 6])
        mime = "image/png"
    elif fmt in ("webp",):
        ok, buf = cv2.imencode(".webp", image, [int(cv2.IMWRITE_WEBP_QUALITY), quality])
        mime = "image/webp"
    else:
        quality = max(30, min(100, int(quality or 90)))
        ok, buf = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        mime = "image/jpeg"

    if not ok:
        raise ValueError("Không thể mã hóa ảnh ghép.")

    return buf.tobytes(), mime


def make_stitched_preview(image: np.ndarray, max_preview_dim: int = 1600, quality: int = 80) -> bytes:
    """Tạo bản xem trước nén nhanh của ảnh ghép để hiển thị mượt mà trên trình duyệt."""
    h, w = image.shape[:2]
    longest = max(h, w)
    if longest <= max_preview_dim:
        thumb = image
    else:
        scale = float(max_preview_dim) / float(longest)
        nw = max(1, int(round(w * scale)))
        nh = max(1, int(round(h * scale)))
        thumb = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_AREA)

    ok, buf = cv2.imencode(".jpg", thumb, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise ValueError("Không thể tạo ảnh xem trước.")
    return buf.tobytes()
