import os
import cv2
import numpy as np
from typing import Tuple, Optional, List


def order_points(pts: np.ndarray) -> np.ndarray:
    """
    Sắp xếp 4 điểm theo thứ tự chuẩn: top-left, top-right, bottom-right, bottom-left.
    pts: mảng numpy shape (4, 2)
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def expand_quad(pts: np.ndarray, img_shape: Tuple[int, int], margin_percent: float = 0.02) -> np.ndarray:
    """
    Giãn rộng hoặc thu hẹp đa giác 4 điểm hoặc 6 điểm theo tỉ lệ phần trăm từ tâm đối tượng.
    margin_percent > 0: giãn rộng (thêm lề)
    margin_percent < 0: thu hẹp (cắt bớt rìa)
    """
    pts = np.asarray(pts, dtype=np.float32)
    h, w = img_shape[:2]

    centroid = np.mean(pts, axis=0)
    expanded = np.zeros_like(pts)
    scale = 1.0 + (margin_percent * 2.0)

    for i in range(len(pts)):
        vec = pts[i] - centroid
        expanded[i] = centroid + vec * scale

    # Cho phép tọa độ ra ngoài mép một chút để lấy trọn viền giấy
    expanded[:, 0] = np.clip(expanded[:, 0], -w * 0.25, w * 1.25)
    expanded[:, 1] = np.clip(expanded[:, 1], -h * 0.25, h * 1.25)
    return expanded


def find_quad_contour(binary_img: np.ndarray, min_area: float) -> Optional[np.ndarray]:
    """Tìm tứ giác tối ưu nhất từ bản đồ nhị phân cạnh."""
    contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        contours, _ = cv2.findContours(binary_img, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area:
            continue

        peri = cv2.arcLength(c, True)
        for eps in [0.015, 0.02, 0.03, 0.04, 0.05]:
            approx = cv2.approxPolyDP(c, eps * peri, True)
            if len(approx) == 4 and cv2.isContourConvex(approx):
                return approx.reshape(4, 2)

    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area:
            continue
        hull = cv2.convexHull(c)
        peri = cv2.arcLength(hull, True)
        for eps in [0.015, 0.02, 0.03, 0.04, 0.05]:
            approx = cv2.approxPolyDP(hull, eps * peri, True)
            if len(approx) == 4 and cv2.isContourConvex(approx):
                return approx.reshape(4, 2)

    return None


def detect_document_corners(image: np.ndarray, margin_percent: float = 0.0) -> Tuple[np.ndarray, bool]:
    """
    Tự động nhận diện 4 góc mép tài liệu từ ảnh chụp.
    Trả về (corners, detected_flag). corners là mảng 4x2 float32 theo thứ tự TL, TR, BR, BL.
    """
    orig_h, orig_w = image.shape[:2]

    target_height = 800.0
    ratio = orig_h / target_height
    target_width = int(orig_w / ratio)
    resized = cv2.resize(image, (target_width, int(target_height)), interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY) if len(resized.shape) == 3 else resized.copy()
    smooth = cv2.bilateralFilter(gray, 9, 75, 75)
    min_area = (resized.shape[0] * resized.shape[1]) * 0.15

    best_quad = None

    # Pass 1: Otsu
    blur = cv2.GaussianBlur(smooth, (5, 5), 0)
    _, thresh_otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thresh_otsu = cv2.morphologyEx(thresh_otsu, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9)))
    best_quad = find_quad_contour(thresh_otsu, min_area)

    # Pass 2: Canny
    if best_quad is None:
        closed = cv2.morphologyEx(smooth, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)))
        edges = cv2.Canny(closed, 30, 120)
        edges = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
        best_quad = find_quad_contour(edges, min_area)

    # Pass 3: Morphological Gradient
    if best_quad is None:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        gradient = cv2.morphologyEx(smooth, cv2.MORPH_GRADIENT, kernel)
        _, grad_thresh = cv2.threshold(gradient, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        best_quad = find_quad_contour(grad_thresh, min_area)

    detected = True
    if best_quad is None:
        detected = False
        inset_x = int(orig_w * 0.02)
        inset_y = int(orig_h * 0.02)
        corners = np.array([
            [inset_x, inset_y],
            [orig_w - inset_x, inset_y],
            [orig_w - inset_x, orig_h - inset_y],
            [inset_x, orig_h - inset_y]
        ], dtype="float32")
    else:
        corners = (best_quad * ratio).astype("float32")
        corners = order_points(corners)

    if margin_percent != 0.0:
        corners = expand_quad(corners, (orig_h, orig_w), margin_percent)

    return corners, detected


def six_point_book_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """
    Nắn thẳng tài liệu dạng 2 trang dính nhau (Sách / Hộ chiếu mở đôi) dựa trên 6 điểm:
        0: Top-Left (Góc trên-trái)
        1: Top-Middle (Gáy trên / điểm giữa trên)
        2: Top-Right (Góc trên-phải)
        3: Bottom-Right (Góc dưới-phải)
        4: Bottom-Middle (Gáy dưới / điểm giữa dưới)
        5: Bottom-Left (Góc dưới-trái)
    Chia đôi thành 2 trang (trái & phải), nắn thẳng từng trang và ghép phẳng hoàn hảo.
    """
    pts = np.asarray(pts, dtype=np.float32)
    h, w = image.shape[:2]
    min_x = np.min(pts[:, 0])
    max_x = np.max(pts[:, 0])
    min_y = np.min(pts[:, 1])
    max_y = np.max(pts[:, 1])

    pad_left = int(max(0, -min_x + 10))
    pad_top = int(max(0, -min_y + 10))
    pad_right = int(max(0, max_x - (w - 1) + 10))
    pad_bottom = int(max(0, max_y - (h - 1) + 10))

    if pad_left > 0 or pad_top > 0 or pad_right > 0 or pad_bottom > 0:
        padded_img = cv2.copyMakeBorder(
            image,
            pad_top, pad_bottom, pad_left, pad_right,
            borderType=cv2.BORDER_REPLICATE
        )
        adj_pts = pts.copy()
        adj_pts[:, 0] += pad_left
        adj_pts[:, 1] += pad_top
    else:
        padded_img = image
        adj_pts = pts.copy()

    tl, tm, tr, br, bm, bl = adj_pts

    # Kích thước ước tính trang trái & trang phải
    top_l = np.hypot(tm[0] - tl[0], tm[1] - tl[1])
    bot_l = np.hypot(bm[0] - bl[0], bm[1] - bl[1])
    w_l = max(int(round(max(top_l, bot_l))), 50)

    top_r = np.hypot(tr[0] - tm[0], tr[1] - tm[1])
    bot_r = np.hypot(br[0] - bm[0], br[1] - bm[1])
    w_r = max(int(round(max(top_r, bot_r))), 50)

    h_l = np.hypot(bl[0] - tl[0], bl[1] - tl[1])
    h_m = np.hypot(bm[0] - tm[0], bm[1] - tm[1])
    h_r = np.hypot(br[0] - tr[0], br[1] - tr[1])
    target_h = max(int(round(max(h_l, h_m, h_r))), 50)

    # 2 trang bằng nhau cân đối
    page_w = max(w_l, w_r)

    # Nắn trang trái: [TL, TM, BM, BL] -> [0..page_w, 0..target_h]
    src_l = np.array([tl, tm, bm, bl], dtype=np.float32)
    dst_l = np.array([
        [0, 0],
        [page_w, 0],
        [page_w, target_h],
        [0, target_h]
    ], dtype=np.float32)
    m_l = cv2.getPerspectiveTransform(src_l, dst_l)
    warp_l = cv2.warpPerspective(
        padded_img, m_l, (page_w, target_h),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )

    # Nắn trang phải: [TM, TR, BR, BM] -> [0..page_w, 0..target_h]
    src_r = np.array([tm, tr, br, bm], dtype=np.float32)
    dst_r = np.array([
        [0, 0],
        [page_w, 0],
        [page_w, target_h],
        [0, target_h]
    ], dtype=np.float32)
    m_r = cv2.getPerspectiveTransform(src_r, dst_r)
    warp_r = cv2.warpPerspective(
        padded_img, m_r, (page_w, target_h),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )

    # Ghép phẳng 2 trang liền nhau tại trục gáy
    combined = np.hstack([warp_l, warp_r])
    return combined


def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """
    Nắn thẳng tứ giác (4 điểm) hoặc sách mở đôi (6 điểm) thành tài liệu phẳng.
    Tự động xử lý phần đệm ngoài biên ảnh nếu điểm nằm ngoài khung hình.
    """
    pts = np.asarray(pts, dtype=np.float32)
    if len(pts) == 6:
        return six_point_book_transform(image, pts)

    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    h, w = image.shape[:2]
    min_x = np.min(rect[:, 0])
    max_x = np.max(rect[:, 0])
    min_y = np.min(rect[:, 1])
    max_y = np.max(rect[:, 1])

    pad_left = int(max(0, -min_x + 10))
    pad_top = int(max(0, -min_y + 10))
    pad_right = int(max(0, max_x - (w - 1) + 10))
    pad_bottom = int(max(0, max_y - (h - 1) + 10))

    if pad_left > 0 or pad_top > 0 or pad_right > 0 or pad_bottom > 0:
        padded_img = cv2.copyMakeBorder(
            image,
            pad_top, pad_bottom, pad_left, pad_right,
            borderType=cv2.BORDER_REPLICATE
        )
        adjusted_rect = rect.copy()
        adjusted_rect[:, 0] += pad_left
        adjusted_rect[:, 1] += pad_top
    else:
        padded_img = image
        adjusted_rect = rect

    (tl, tr, br, bl) = adjusted_rect

    width_a = np.hypot(br[0] - bl[0], br[1] - bl[1])
    width_b = np.hypot(tr[0] - tl[0], tr[1] - tl[1])
    max_width = max(int(width_a), int(width_b), 50)

    height_a = np.hypot(tr[0] - br[0], tr[1] - br[1])
    height_b = np.hypot(tl[0] - bl[0], bl[1] - tl[1])
    max_height = max(int(height_a), int(height_b), 50)

    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]
    ], dtype="float32")

    m = cv2.getPerspectiveTransform(adjusted_rect, dst)
    warped = cv2.warpPerspective(
        padded_img,
        m,
        (max_width, max_height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )
    return warped
