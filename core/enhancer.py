import cv2
import numpy as np


def rotate_image(image: np.ndarray, angle: int) -> np.ndarray:
    """Xoay ảnh theo góc (90, 180, 270 độ)."""
    angle = angle % 360
    if angle == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    elif angle == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image


def remove_crease_shadows_and_folds(image: np.ndarray, strength: float = 0.6) -> np.ndarray:
    """Khử bóng đổ, nếp gấp không đều trên bề mặt trang giấy (giữ nguyên màu mực/con dấu)."""
    if strength <= 0.01:
        return image.copy()

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_chan, a_chan, b_chan = cv2.split(lab)
    h, w = image.shape[:2]

    k = max(51, int(min(h, w) * 0.12)) | 1
    bg = cv2.GaussianBlur(l_chan, (k, k), 0).astype(np.float32) + 1.0

    l_float = l_chan.astype(np.float32)
    normalized_l = (l_float / bg) * 255.0
    normalized_l = np.clip(normalized_l, 0, 255).astype(np.uint8)

    l_bleached = cv2.addWeighted(normalized_l, strength, l_chan, 1.0 - strength, 0)
    result_lab = cv2.merge([l_bleached, a_chan, b_chan])
    return cv2.cvtColor(result_lab, cv2.COLOR_LAB2BGR)


def unsharp_mask(image: np.ndarray, sigma: float = 1.0, strength: float = 0.6, threshold: int = 2) -> np.ndarray:
    """Làm nét các nét chữ mà không tạo hạt sạn (grain)."""
    if strength <= 0.01:
        return image.copy()

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    blurred = cv2.GaussianBlur(l, (0, 0), sigma)
    diff = l.astype(np.float32) - blurred.astype(np.float32)

    mask = np.abs(diff) > threshold
    sharpened_l = l.astype(np.float32) + strength * diff * mask
    sharpened_l = np.clip(sharpened_l, 0, 255).astype(np.uint8)

    merged = cv2.merge([sharpened_l, a, b])
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def restore_aged_yellowed_paper(image: np.ndarray) -> np.ndarray:
    """Phục hồi tài liệu ố vàng, khử vết ố nâu của giấy cũ nhưng giữ màu mực."""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    h, w = image.shape[:2]

    k_size = max(31, int(min(h, w) * 0.06)) | 1
    bg_b = cv2.GaussianBlur(b, (k_size, k_size), 0).astype(np.float32)
    bg_a = cv2.GaussianBlur(a, (k_size, k_size), 0).astype(np.float32)

    b_float = b.astype(np.float32)
    a_float = a.astype(np.float32)

    chroma_dist = np.sqrt((a_float - 128.0)**2 + (b_float - 128.0)**2)
    is_colored_ink = chroma_dist > 22.0

    neutral_b = 128.0 + (b_float - bg_b) * 0.85
    neutral_a = 128.0 + (a_float - bg_a) * 0.85

    b_clean = np.where(is_colored_ink, b_float, neutral_b)
    a_clean = np.where(is_colored_ink, a_float, neutral_a)

    b_clean = np.clip(b_clean, 0, 255).astype(np.uint8)
    a_clean = np.clip(a_clean, 0, 255).astype(np.uint8)

    bg_l = cv2.GaussianBlur(l, (k_size, k_size), 0).astype(np.float32) + 1.0
    norm_l = (l.astype(np.float32) / bg_l) * 255.0
    norm_l = np.clip(norm_l * 1.05 + 5, 0, 255).astype(np.uint8)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_restored = clahe.apply(norm_l)

    merged = cv2.merge([l_restored, a_clean, b_clean])
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def remove_bleedthrough_showthrough(image: np.ndarray) -> np.ndarray:
    """Khử mực thấm ngược từ mặt sau của giấy mỏng/2 mặt."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
    h, w = image.shape[:2]

    k = max(25, int(min(h, w) * 0.04)) | 1
    bg = cv2.GaussianBlur(gray, (k, k), 0)
    diff = bg.astype(np.float32) - gray.astype(np.float32)

    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)

    front_mask = (grad_mag > 18.0) | (diff > 45.0)

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    bg_l = cv2.GaussianBlur(l, (k, k), 0)
    cleaned_l = np.where(front_mask, l, np.maximum(l, bg_l))
    cleaned_l = np.clip(cleaned_l.astype(np.float32) * 1.04 + 6, 0, 255).astype(np.uint8)

    merged = cv2.merge([cleaned_l, a, b])
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def boost_stamp_and_signatures(image: np.ndarray) -> np.ndarray:
    """Tăng tương phản và độ tươi cho con dấu đỏ và chữ ký xanh."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h_chan, s_chan, v_chan = cv2.split(hsv)

    red_mask1 = (h_chan <= 12) & (s_chan > 40)
    red_mask2 = (h_chan >= 168) & (s_chan > 40)
    red_mask = red_mask1 | red_mask2

    blue_mask = (h_chan >= 95) & (h_chan <= 135) & (s_chan > 35)
    stamp_mask = red_mask | blue_mask

    s_boosted = s_chan.astype(np.float32)
    s_boosted[stamp_mask] = np.clip(s_boosted[stamp_mask] * 1.6 + 25, 0, 255)
    s_boosted[~stamp_mask] = np.clip(s_boosted[~stamp_mask] * 0.9, 0, 255)
    s_final = s_boosted.astype(np.uint8)

    h_dim, w_dim = image.shape[:2]
    k = max(25, int(min(h_dim, w_dim) * 0.05)) | 1
    bg_v = cv2.GaussianBlur(v_chan, (k, k), 0).astype(np.float32) + 1.0
    norm_v = (v_chan.astype(np.float32) / bg_v) * 255.0
    v_final = np.clip(norm_v * 1.06 + 8, 0, 255).astype(np.uint8)

    merged_hsv = cv2.merge([h_chan, s_final, v_final])
    return cv2.cvtColor(merged_hsv, cv2.COLOR_HSV2BGR)


def enhance_magic_color(image: np.ndarray) -> np.ndarray:
    """Magic Color: Làm trắng tinh nền giấy, màu mực tươi sáng và chữ sắc nét."""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    h, w = image.shape[:2]

    k = max(25, int(min(h, w) * 0.05)) | 1
    dilated = cv2.dilate(l, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    bg = cv2.GaussianBlur(dilated, (k, k), 0).astype(np.float32) + 1.0

    norm_l = (l.astype(np.float32) / bg) * 255.0
    norm_l = np.clip(norm_l * 1.12 + 10, 0, 255).astype(np.uint8)

    clahe = cv2.createCLAHE(clipLimit=1.8, tileGridSize=(8, 8))
    norm_l = clahe.apply(norm_l)

    merged_lab = cv2.merge([norm_l, a, b])
    bgr_temp = cv2.cvtColor(merged_lab, cv2.COLOR_LAB2BGR)
    hsv = cv2.cvtColor(bgr_temp, cv2.COLOR_BGR2HSV)
    h_c, s_c, v_c = cv2.split(hsv)

    s_boost = np.clip(s_c.astype(np.float32) * 1.4 + 5, 0, 255).astype(np.uint8)
    enhanced_hsv = cv2.merge([h_c, s_boost, v_c])
    return cv2.cvtColor(enhanced_hsv, cv2.COLOR_HSV2BGR)


def enhance_document(
    image: np.ndarray,
    mode: str = "original",
    shadow_reduction: float = 0.5,
    sharpness: float = 0.5,
    contrast: float = 0.0,
    brightness: float = 0.0
) -> np.ndarray:
    """
    Áp dụng bộ lọc tăng cường, độ tương phản và độ sáng cho ảnh tài liệu.
    Các chế độ:
      - 'original': Giữ nguyên màu ảnh gốc (vẫn nhận chỉnh sáng / tương phản nếu có).
      - 'clean_bg': Làm trắng sạch nền giấy.
      - 'sharp_text': Làm nét chữ, tăng tương phản chữ mờ.
      - 'bw_scan': Quét đen trắng chuẩn in ấn văn phòng.
      - 'magic_color': Màu sắc tươi sáng, nền trắng bóc.
      - 'high_contrast_stamp': Nổi bật con dấu đỏ & chữ ký.
      - 'restore_yellowed': Khử ố vàng giấy cũ.
      - 'remove_bleedthrough': Khử mực thấm mặt sau.
      - 'natural': Cân bằng tự nhiên.
    """
    # Nếu mode == original và không chỉnh sáng/tương phản -> trả về ảnh gốc nhanh
    if mode == "original" and abs(brightness) <= 0.01 and contrast <= 0.01:
        return image.copy()

    # Bước 1: Khử bóng nếp gấp nếu có chế độ nâng cao
    if mode != "original" and shadow_reduction > 0:
        img_balanced = remove_crease_shadows_and_folds(image, strength=shadow_reduction)
    else:
        img_balanced = image.copy()

    # Bước 2: Xử lý theo chế độ bộ lọc
    if mode == "magic_color":
        img_result = enhance_magic_color(img_balanced)

    elif mode == "restore_yellowed":
        img_result = restore_aged_yellowed_paper(img_balanced)

    elif mode == "remove_bleedthrough":
        img_result = remove_bleedthrough_showthrough(img_balanced)

    elif mode == "high_contrast_stamp":
        img_result = boost_stamp_and_signatures(img_balanced)

    elif mode == "bw_scan":
        gray = cv2.cvtColor(img_balanced, cv2.COLOR_BGR2GRAY)
        k_size = max(25, int(min(image.shape[:2]) * 0.05)) | 1
        bg = cv2.GaussianBlur(gray, (k_size, k_size), 0)
        norm = (gray.astype(np.float32) / (bg.astype(np.float32) + 1.0)) * 255.0
        norm = np.clip(norm, 0, 255).astype(np.uint8)

        clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
        enhanced = clahe.apply(norm)

        blur = cv2.GaussianBlur(enhanced, (0, 0), 1.2)
        sharp = cv2.addWeighted(enhanced, 1.5, blur, -0.5, 0)
        img_result = cv2.cvtColor(sharp, cv2.COLOR_GRAY2BGR)

    elif mode == "clean_bg":
        lab = cv2.cvtColor(img_balanced, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        k_size = max(25, int(min(image.shape[:2]) * 0.05)) | 1
        bg = cv2.GaussianBlur(l, (k_size, k_size), 0)
        norm_l = (l.astype(np.float32) / (bg.astype(np.float32) + 1.0)) * 255.0
        norm_l = np.clip(norm_l * 1.06 + 8, 0, 255).astype(np.uint8)

        clahe = cv2.createCLAHE(clipLimit=1.6, tileGridSize=(8, 8))
        norm_l = clahe.apply(norm_l)

        merged = cv2.merge([norm_l, a, b])
        img_result = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    elif mode == "sharp_text":
        lab = cv2.cvtColor(img_balanced, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=2.4, tileGridSize=(8, 8))
        l_clahe = clahe.apply(l)

        merged = cv2.merge([l_clahe, a, b])
        img_result = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    elif mode == "natural":
        lab = cv2.cvtColor(img_balanced, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
        l = clahe.apply(l)
        merged = cv2.merge([l, a, b])
        img_result = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    else:
        # mode == "original" hoặc không xác định
        img_result = img_balanced

    # Bước 3: Tăng giảm tương phản (Contrast)
    if contrast > 0.01:
        lab_c = cv2.cvtColor(img_result, cv2.COLOR_BGR2LAB)
        l_c, a_c, b_c = cv2.split(lab_c)
        clahe = cv2.createCLAHE(clipLimit=1.0 + (contrast * 3.5), tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l_c)
        factor = 1.0 + contrast * 0.75
        l_float = l_enhanced.astype(np.float32)
        l_stretched = np.clip(128.0 + (l_float - 128.0) * factor, 0, 255).astype(np.uint8)
        img_result = cv2.cvtColor(cv2.merge([l_stretched, a_c, b_c]), cv2.COLOR_LAB2BGR)

    # Bước 4: Làm nét chữ (chỉ khi có bật)
    if mode != "original" and sharpness > 0:
        img_result = unsharp_mask(img_result, sigma=1.0, strength=sharpness)

    # Bước 5: Chỉnh độ sáng (Brightness)
    if abs(brightness) > 0.01:
        img_float = img_result.astype(np.float32) + (brightness * 50.0)
        img_result = np.clip(img_float, 0, 255).astype(np.uint8)

    return img_result
