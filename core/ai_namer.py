import os
import re
import json
import base64
import datetime
from typing import List, Tuple, Optional, Dict, Any
import cv2
import numpy as np
from unidecode import unidecode

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

# Lazy-loaded RapidOCR engine
_OCR_ENGINE = None

def get_ocr_engine():
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _OCR_ENGINE = RapidOCR()
        except Exception as e:
            print(f"[Warning] Could not initialize RapidOCR: {e}")
            _OCR_ENGINE = False
    return _OCR_ENGINE if _OCR_ENGINE is not False else None


def load_config() -> Dict[str, Any]:
    default_config = {
        "openai_api_key": "",
        "openai_model": "gpt-4o-mini",
        "openai_base_url": "https://api.openai.com/v1"
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    default_config.update(data)
        except Exception as e:
            print(f"[Warning] Error reading {CONFIG_PATH}: {e}")

    # Fallback to env var
    if not default_config["openai_api_key"]:
        default_config["openai_api_key"] = os.environ.get("OPENAI_API_KEY", "")

    return default_config


def save_config(config_data: Dict[str, Any]) -> bool:
    try:
        cur = load_config()
        cur.update(config_data)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cur, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[Error] Failed to save config: {e}")
        return False


def clean_filename_str(text: str) -> str:
    """Loại bỏ ký tự cấm của hệ điều hành và chuẩn hóa thành chuỗi đặt tên file đẹp."""
    if not text:
        return "tai_lieu"
    # Giữ các ký tự chữ, số, gạch dưới, gạch ngang, khoảng trắng
    text = re.sub(r'[\\/*?:"<>|]', "", text)
    text = text.replace(" ", "_").replace("-", "_")
    # Gộp nhiều dấu gạch dưới liên tiếp
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:80] if text else "tai_lieu"


DOCUMENT_PATTERNS = [
    (r"\b(chung\s*nhan\s*ket\s*hon|ket\s*hon|marriage)\b", "Giay_Chung_Nhan_Ket_Hon"),
    (r"\b(khai\s*sinh|birth\s*cert)\b", "Giay_Khai_Sinh"),
    (r"\b(can\s*cuoc|cccd|cmnd|the\s*can\s*cuoc|identity)\b", "Can_Cuoc_Cong_Dan"),
    (r"\b(ho\s*chieu|passport)\b", "Ho_Chieu_Passport"),
    (r"\b(bang\s*lai|giay\s*phep\s*lai\s*xe|driver)\b", "Giay_Phep_Lai_Xe"),
    (r"\b(so\s*ho\s*khau|ho\s*khau)\b", "So_Ho_Khau"),
    (r"\b(hop\s*dong\s*thue\s*nha|thue\s*nha)\b", "Hop_Dong_Thue_Nha"),
    (r"\b(hop\s*dong\s*lao\s*dong)\b", "Hop_Dong_Lao_Dong"),
    (r"\b(hop\s*dong\s*mua\s*ban)\b", "Hop_Dong_Mua_Ban"),
    (r"\b(hop\s*dong)\b", "Hop_Dong"),
    (r"\b(hoa\s*don|invoice|gtgt|vat)\b", "Hoa_Don_GTGT"),
    (r"\b(bang\s*diem|transcript)\b", "Bang_Diem"),
    (r"\b(bang\s*tot\s*nghiep|diploma)\b", "Bang_Tot_Nghiep"),
    (r"\b(ban\s*dich\s*cong\s*chung|notary|translation)\b", "Ban_Dich_Cong_Chung"),
    (r"\b(giay\s*xac\s*nhan|confirmation)\b", "Giay_Xac_Nhan"),
    (r"\b(don\s*xin\s*viec|cv|resume)\b", "Don_Xin_Viec"),
    (r"\b(don\s*thuoc|benh\s*an)\b", "Ho_So_Benh_An"),
]


def extract_text_with_ocr(image: np.ndarray) -> List[str]:
    """Chạy OCR đọc phần tiêu đề và nội dung nửa trên của tài liệu."""
    engine = get_ocr_engine()
    if engine is None or image is None:
        return []

    try:
        h, w = image.shape[:2]
        # Crop nửa trên tài liệu để đọc tiêu đề và tên người
        crop = image[0:int(h * 0.55), :]
        result, _ = engine(crop)
        lines = []
        if result:
            for item in result:
                confidence = item[2]
                if confidence > 0.40:
                    text = item[1].strip()
                    if len(text) >= 2:
                        lines.append(text)
        return lines
    except Exception as e:
        print(f"[Warning] OCR extract error: {e}")
        return []


def suggest_name_via_ocr_rules(lines: List[str], fallback_name: str = "") -> Tuple[str, List[str]]:
    """Phân tích nội dung OCR bằng quy tắc nhận diện văn bản hành chính Việt Nam."""
    today_str = datetime.date.today().strftime("%Y%m%d")
    combined = " ".join(lines)
    combined_ascii = unidecode(combined).lower()

    detected_type = None
    for pattern, label in DOCUMENT_PATTERNS:
        if re.search(pattern, combined_ascii):
            detected_type = label
            break

    # Tìm tên người sau các cụm từ nhận diện
    person_name = ""
    name_match = re.search(r"(?:ho\s*va\s*ten|ho\s*ten|ong|ba|chong|vo|cho\s*ong|cho\s*ba)[:\s]+([A-ZÀ-Ỹa-zà-ỹ\s]{3,30})", combined, re.IGNORECASE)
    if name_match:
        raw_person = name_match.group(1).strip()
        # Lọc nếu quá dài hoặc dính chữ thừa
        words = raw_person.split()
        if 2 <= len(words) <= 5:
            person_name = "_".join([unidecode(w).capitalize() for w in words])

    if not detected_type:
        if fallback_name:
            clean_fb = clean_filename_str(unidecode(fallback_name))
            detected_type = clean_fb if len(clean_fb) > 2 else "Tai_Lieu"
        else:
            detected_type = "Tai_Lieu_Tong_Hop"

    if person_name:
        primary = f"{detected_type}_{person_name}"
    else:
        primary = detected_type

    suggestions = [
        primary,
        f"{primary}_{today_str}",
        f"{detected_type}",
        f"{detected_type}_{today_str}",
    ]

    clean_suggestions = []
    seen = set()
    for s in suggestions:
        cs = clean_filename_str(s)
        if cs and cs not in seen:
            seen.add(cs)
            clean_suggestions.append(cs)

    return clean_suggestions[0], clean_suggestions


def suggest_name_via_chatgpt(
    image: Optional[np.ndarray],
    page_names: List[str],
    api_key: str,
    model: str = "gpt-4o-mini",
    base_url: str = "https://api.openai.com/v1"
) -> Tuple[Optional[str], List[str]]:
    """Gọi ChatGPT Vision / OpenAI để phân tích tài liệu và đặt tên file cực kỳ thông minh."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)

    system_prompt = (
        "Bạn là trợ lý đặt tên file tài liệu tiếng Việt chuyên nghiệp. "
        "Dựa vào nội dung hình ảnh trang đầu và danh sách tên trang, hãy phân tích loại giấy tờ và thông tin chủ thể chính "
        "(ví dụ: Giấy chứng nhận kết hôn của ai, Giấy khai sinh của ai, Hợp đồng gì). "
        "Đặt tên file ngắn gọn, chuẩn mực, viết hoa chữ cái đầu mỗi từ, nối bằng dấu gạch dưới '_', không chứa ký tự cấm. "
        "Bắt buộc trả về đúng định dạng JSON: "
        '{"primary": "Ten_Chuan_Day_Du", "suggestions": ["Ten_Chuan_Day_Du", "Ten_Ngan_Gon", "Ten_Kem_Ngay"]}'
    )

    user_content = []
    names_context = f"Danh sách các trang tài liệu: {', '.join(page_names[:8])}"
    user_content.append({"type": "text", "text": names_context})

    if image is not None:
        # Resize nhỏ để tiết kiệm token và xử lý siêu tốc (< 1000px)
        h, w = image.shape[:2]
        max_dim = 1000
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            img_small = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        else:
            img_small = image

        ok, buf = cv2.imencode(".jpg", img_small, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ok:
            b64_str = base64.b64encode(buf.tobytes()).decode("utf-8")
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64_str}",
                    "detail": "low"
                }
            })

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=200,
    )

    content_str = response.choices[0].message.content
    data = json.loads(content_str)
    primary = clean_filename_str(data.get("primary", ""))
    raw_suggs = data.get("suggestions", [])
    suggestions = [clean_filename_str(s) for s in raw_suggs if s]
    if primary and primary not in suggestions:
        suggestions.insert(0, primary)

    return primary, suggestions


def suggest_document_filename(
    first_page_image: Optional[np.ndarray],
    page_names: List[str]
) -> Dict[str, Any]:
    """Hàm tổng hợp gợi ý tên file thông minh (Ưu tiên ChatGPT nếu có API Key, tự động dự phòng sang RapidOCR)."""
    cfg = load_config()
    api_key = cfg.get("openai_api_key", "").strip()
    model = cfg.get("openai_model", "gpt-4o-mini").strip()
    base_url = cfg.get("openai_base_url", "https://api.openai.com/v1").strip()

    # 1. Thử gọi ChatGPT nếu có API Key
    if api_key:
        try:
            primary, suggestions = suggest_name_via_chatgpt(
                image=first_page_image,
                page_names=page_names,
                api_key=api_key,
                model=model,
                base_url=base_url
            )
            if primary:
                return {
                    "success": True,
                    "engine": "chatgpt",
                    "primary": primary,
                    "suggestions": suggestions,
                    "message": f"Gợi ý bởi AI ({model})"
                }
        except Exception as e:
            print(f"[Warning] ChatGPT API call failed: {e}. Falling back to OCR...")

    # 2. Dự phòng bằng RapidOCR cục bộ
    fallback_name = page_names[0] if page_names else ""
    ocr_lines = []
    if first_page_image is not None:
        ocr_lines = extract_text_with_ocr(first_page_image)

    primary, suggestions = suggest_name_via_ocr_rules(ocr_lines, fallback_name=fallback_name)

    return {
        "success": True,
        "engine": "ocr_local",
        "primary": primary,
        "suggestions": suggestions,
        "has_api_key": bool(api_key),
        "message": "Gợi ý tự động bởi nhận diện tài liệu" if not api_key else "Gợi ý bởi nhận diện tài liệu (ChatGPT dự phòng)"
    }
