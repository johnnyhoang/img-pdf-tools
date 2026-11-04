import io
import os
import zipfile
import urllib.parse
from typing import List, Optional
import cv2
import numpy as np

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from core.pagemanager import PageManager
from core.detector import detect_document_corners
from core.pdf_engine import (
    build_pdf_from_images,
    build_pdf_from_pages,
    compress_image_to_bytes,
    estimate_images_size,
    estimate_pdf_size,
)
from core.pdf_stitcher import (
    stitch_images,
    encode_stitched_image,
    make_stitched_preview,
    parse_color_hex,
)

app = FastAPI(title="PDF & Image Studio", version="1.3.0")

# Middleware ngăn trình duyệt lưu cache file tĩnh trong chế độ làm việc cục bộ
@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.startswith("/js/") or path.startswith("/css/") or path.endswith(".html"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Khởi tạo PageManager quản lý các trang tài liệu
manager = PageManager()

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)


# ==========================================
# CÁC MODEL YÊU CẦU (REQUEST SCHEMAS)
# ==========================================

class ReorderRequest(BaseModel):
    page_ids: List[str]


class RotateRequest(BaseModel):
    page_ids: Optional[List[str]] = None
    angle_delta: int = 90


class EnhanceRequest(BaseModel):
    page_ids: Optional[List[str]] = None
    filter_mode: str = "original"


class DeleteRequest(BaseModel):
    page_ids: List[str]


class DuplicateRequest(BaseModel):
    page_id: str


class CropRectRequest(BaseModel):
    page_id: str
    x: int
    y: int
    width: int
    height: int


class CropMarginsRequest(BaseModel):
    page_id: str
    top: int = 0
    bottom: int = 0
    left: int = 0
    right: int = 0


class ResizePageRequest(BaseModel):
    page_id: Optional[str] = None
    page_ids: Optional[List[str]] = None
    width: int
    height: Optional[int] = None
    fit_mode: str = "exact"


class ScalePageRequest(BaseModel):
    page_id: str
    percent: float = 100.0


class PageSetupRequest(BaseModel):
    page_ids: Optional[List[str]] = None
    page_id: Optional[str] = None
    page_size: Optional[str] = None       # "A4", "A3", "A5", "letter", "fit_image"
    orientation: Optional[str] = None     # "portrait", "landscape"
    placement: Optional[str] = None       # "center", "top", "fit"
    scale_percent: Optional[float] = None # e.g. 50, 75, 100


class DocumentPageSetupRequest(BaseModel):
    page_size: str = "fit_image"          # "fit_image", "A4"
    orientation: str = "portrait"         # "portrait", "landscape"


class AutoDetectCornersRequest(BaseModel):
    margin_percent: float = 0.0


class PageEditRequest(BaseModel):
    corners: Optional[List[List[float]]] = None
    rotation: Optional[int] = None
    brightness: Optional[float] = None
    contrast: Optional[float] = None
    filter_mode: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    image_scale: Optional[float] = None
    apply_to_selected: bool = False
    selected_page_ids: Optional[List[str]] = None


class PageActionRequest(BaseModel):
    page_id: str


class ExportPdfRequest(BaseModel):
    page_ids: Optional[List[str]] = None
    layout_mode: str = "original"
    quality: int = 85
    filename: Optional[str] = "tai_lieu.pdf"


class EstimatePdfSizeRequest(BaseModel):
    page_ids: Optional[List[str]] = None
    layout_mode: str = "original"
    quality: int = 85


class EstimateSizeRequest(BaseModel):
    page_ids: Optional[List[str]] = None
    format: str = "jpeg"
    quality: int = 85
    max_dimension: Optional[int] = None


class StitchPreviewRequest(BaseModel):
    page_ids: Optional[List[str]] = None
    layout: str = "grid"
    cols: int = 3
    spacing: int = 24
    padding: int = 32
    bg_color: str = "#ffffff"
    draw_border: bool = True
    last_row_align: str = "center"
    scale: float = 1.0


class StitchDownloadRequest(BaseModel):
    page_ids: Optional[List[str]] = None
    layout: str = "grid"
    cols: int = 3
    spacing: int = 24
    padding: int = 32
    bg_color: str = "#ffffff"
    draw_border: bool = True
    last_row_align: str = "center"
    scale: float = 1.0
    format: str = "jpeg"
    quality: int = 90
    filename: Optional[str] = "anh_ghep.jpg"


class ExportZipRequest(BaseModel):
    page_ids: Optional[List[str]] = None
    format: str = "jpeg"
    quality: int = 85
    max_dimension: Optional[int] = None
    filename: Optional[str] = "danh_sach_anh.zip"


class ConfigUpdateRequest(BaseModel):
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None


class SavePdfDirectRequest(BaseModel):
    layout_mode: str = "original"
    quality: int = 85


class SavePdfAsRequest(BaseModel):
    suggested_name: Optional[str] = "tai_lieu_dong_nhat.pdf"
    layout_mode: str = "original"
    quality: int = 85


# Trạng thái tệp PDF nguồn đang mở để hỗ trợ lưu trực tiếp
current_source_pdf: Optional[dict] = None


# ==========================================
# CÁC API QUẢN LÝ TRANG & LẮP GHÉP
# ==========================================

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Nạp nhiều ảnh hoặc file PDF cùng lúc."""
    if not files:
        raise HTTPException(status_code=400, detail="Vui lòng chọn ít nhất 1 tệp tin.")

    uploaded_count = 0
    errors = []

    for file in files:
        contents = await file.read()
        fname = file.filename or "tep_tin"
        ext = os.path.splitext(fname)[1].lower()

        try:
            if ext == ".pdf":
                items = await run_in_threadpool(manager.add_pdf, fname, contents)
                uploaded_count += len(items)
            else:
                def _decode_img(data):
                    arr = np.frombuffer(data, np.uint8)
                    return cv2.imdecode(arr, cv2.IMREAD_COLOR)

                img = await run_in_threadpool(_decode_img, contents)
                if img is None:
                    errors.append(f"Không thể đọc định dạng ảnh: {fname}")
                    continue

                manager.add_image(fname, img)
                uploaded_count += 1
        except Exception as e:
            errors.append(f"Lỗi khi xử lý {fname}: {str(e)}")

    pages = manager.list_pages()
    global current_source_pdf
    if len(files) == 1 and (files[0].filename or "").lower().endswith(".pdf"):
        current_source_pdf = {
            "path": "",
            "name": files[0].filename,
            "folder": "",
        }

    return {
        "success": True,
        "uploaded_count": uploaded_count,
        "total_pages": len(pages),
        "pages": pages,
        "source_pdf": current_source_pdf,
        "errors": errors if errors else None,
    }


@app.get("/api/pages")
async def get_pages():
    """Lấy danh sách tất cả các trang hiện có theo thứ tự và khổ trang tài liệu hiện tại."""
    return {
        "success": True,
        "doc_page_size": manager.doc_page_size,
        "doc_orientation": manager.doc_orientation,
        "pages": manager.list_pages(),
    }


@app.get("/api/pages/distinct-dimensions")
async def get_distinct_dimensions():
    """Lấy danh sách các khổ ảnh đang có trong dự án để làm mẫu đồng bộ."""
    return {"success": True, "dimensions": manager.get_distinct_dimensions()}


@app.get("/api/pages/{page_id}/thumb")
async def get_page_thumb(page_id: str):
    """Lấy ảnh thumbnail kích thước nhỏ của trang."""
    page = manager.get_page(page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Không tìm thấy trang yêu cầu.")

    thumb_data = await run_in_threadpool(page.get_thumbnail)
    return Response(
        content=thumb_data,
        media_type="image/jpeg",
        headers={"Cache-Control": "max-age=60"},
    )


@app.get("/api/pages/{page_id}/preview")
async def get_page_preview(page_id: str):
    """Lấy ảnh xem trước độ phân giải cao của trang."""
    page = manager.get_page(page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Không tìm thấy trang yêu cầu.")

    preview_data = await run_in_threadpool(page.get_preview)
    return Response(
        content=preview_data,
        media_type="image/jpeg",
        headers={"Cache-Control": "max-age=60"},
    )


@app.get("/api/pages/{page_id}/original")
async def get_page_original(page_id: str):
    """Lấy ảnh gốc nguyên bản phục vụ việc chấm góc trên canvas."""
    page = manager.get_page(page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Không tìm thấy trang yêu cầu.")

    def _encode_orig():
        ok, buf = cv2.imencode(".jpg", page.original_image, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        return buf.tobytes() if ok else b""

    orig_data = await run_in_threadpool(_encode_orig)
    return Response(
        content=orig_data,
        media_type="image/jpeg",
        headers={"Cache-Control": "max-age=60"},
    )


@app.post("/api/pages/{page_id}/auto-detect-corners")
async def auto_detect_corners(page_id: str, req: AutoDetectCornersRequest = AutoDetectCornersRequest()):
    """Tự động phát hiện 4 góc mép tài liệu trên ảnh gốc."""
    page = manager.get_page(page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Không tìm thấy trang yêu cầu.")

    corners, detected = await run_in_threadpool(
        detect_document_corners, page.original_image, req.margin_percent
    )
    return {
        "success": True,
        "corners": corners.tolist(),
        "detected": bool(detected),
    }


@app.post("/api/pages/{page_id}/edit")
async def edit_page_api(page_id: str, req: PageEditRequest):
    """Áp dụng chỉnh sửa toàn diện: chấm góc (4/6 điểm), xoay, chỉnh sáng/tương phản/bộ lọc, resize/scale."""
    target_ids = [page_id]
    if req.apply_to_selected and req.selected_page_ids:
        target_ids = list(set([page_id] + req.selected_page_ids))

    for pid in target_ids:
        p = manager.get_page(pid)
        if not p:
            continue
        corners_to_apply = req.corners if pid == page_id else p.corners
        p.apply_full_edit(
            corners=corners_to_apply,
            rotation=req.rotation,
            brightness=req.brightness,
            contrast=req.contrast,
            filter_mode=req.filter_mode,
            target_w=req.width,
            target_h=req.height,
            image_scale=req.image_scale,
        )
    return {"success": True, "pages": manager.list_pages()}


@app.post("/api/pages/reorder")
async def reorder_pages(req: ReorderRequest):
    """Thay đổi thứ tự danh sách trang."""
    manager.reorder(req.page_ids)
    return {"success": True, "pages": manager.list_pages()}


@app.post("/api/pages/rotate")
async def rotate_pages(req: RotateRequest):
    """Xoay 1 hoặc nhiều trang theo góc delta (90, 180, 270)."""
    manager.rotate_pages(req.page_ids or [], angle_delta=req.angle_delta)
    return {"success": True, "pages": manager.list_pages()}


@app.post("/api/pages/enhance")
async def enhance_pages(req: EnhanceRequest):
    """Áp dụng bộ lọc cho 1 hoặc nhiều trang."""
    manager.set_filter(req.page_ids or [], filter_mode=req.filter_mode)
    return {"success": True, "pages": manager.list_pages()}


@app.post("/api/pages/crop")
async def crop_page(req: CropRectRequest):
    """Cắt xén vùng chữ nhật của 1 trang riêng biệt."""
    ok = manager.crop_page_rect(req.page_id, req.x, req.y, req.width, req.height)
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy trang để cắt xén.")
    return {"success": True, "pages": manager.list_pages()}


@app.post("/api/pages/crop-margins")
async def crop_page_margins(req: CropMarginsRequest):
    """Cắt bỏ lề trên, dưới, trái, phải của 1 trang riêng biệt."""
    ok = manager.crop_page_margins(req.page_id, req.top, req.bottom, req.left, req.right)
    if not ok:
        raise HTTPException(status_code=400, detail="Không thể cắt lề với tham số đã chọn.")
    return {"success": True, "pages": manager.list_pages()}


@app.post("/api/document/page-setup")
async def set_document_page_setup_api(req: DocumentPageSetupRequest):
    """Thiết lập khổ trang đồng nhất cho TOÀN BỘ file tài liệu (Document-Level Page Setup)."""
    count = manager.set_document_page_size(req.page_size, req.orientation)
    return {
        "success": True,
        "doc_page_size": manager.doc_page_size,
        "doc_orientation": manager.doc_orientation,
        "count": count,
        "pages": manager.list_pages(),
    }


@app.post("/api/pages/setup")
async def setup_pages_api(req: PageSetupRequest):
    """Thiết lập Khung trang giấy (A4, A3, Fit Image) và vị trí đặt hình trên trang."""
    target_ids = req.page_ids or ([req.page_id] if req.page_id else None)
    scale_factor = (req.scale_percent / 100.0) if req.scale_percent is not None else None
    count = manager.setup_pages(
        page_ids=target_ids,
        page_size=req.page_size,
        orientation=req.orientation,
        placement=req.placement,
        scale=scale_factor,
    )
    return {"success": True, "count": count, "pages": manager.list_pages()}


@app.post("/api/pages/resize")
async def resize_pages(req: ResizePageRequest):
    """Thay đổi kích thước Width x Height của đối tượng hình ảnh."""
    if req.page_ids and len(req.page_ids) > 0:
        count = manager.resize_multiple_page_images(
            req.page_ids,
            req.width,
            req.height,
            fit_mode=req.fit_mode,
        )
        return {"success": True, "modified_count": count, "pages": manager.list_pages()}
    elif req.page_id:
        ok = manager.resize_page_image(
            req.page_id,
            req.width,
            req.height,
            fit_mode=req.fit_mode,
        )
        if not ok:
            raise HTTPException(status_code=404, detail="Không tìm thấy trang để chỉnh kích thước.")
        return {"success": True, "pages": manager.list_pages()}
    else:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp mã trang để chỉnh kích thước.")


@app.post("/api/pages/scale")
async def scale_page(req: ScalePageRequest):
    """Thu phóng tỷ lệ % của đối tượng hình ảnh."""
    ok = manager.scale_page_image(req.page_id, req.percent)
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy trang để thu phóng.")
    return {"success": True, "pages": manager.list_pages()}


@app.post("/api/pages/auto-trim")
async def auto_trim_page(req: PageActionRequest):
    """Tự động phát hiện và cắt bỏ lề trống thừa xung quanh trang."""
    bbox = manager.auto_trim_page(req.page_id)
    if not bbox:
        raise HTTPException(status_code=404, detail="Không tìm thấy trang để tự động cắt lề.")
    return {"success": True, "bbox": bbox, "pages": manager.list_pages()}


@app.post("/api/pages/reset")
async def reset_page(req: PageActionRequest):
    """Khôi phục ảnh gốc nguyên bản của 1 trang."""
    ok = manager.reset_page(req.page_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy trang để khôi phục.")
    return {"success": True, "pages": manager.list_pages()}


@app.post("/api/pages/delete")
async def delete_pages(req: DeleteRequest):
    """Xóa các trang được chọn."""
    deleted_count = manager.delete_pages(req.page_ids)
    return {"success": True, "deleted_count": deleted_count, "pages": manager.list_pages()}


@app.post("/api/pages/duplicate")
async def duplicate_page(req: DuplicateRequest):
    """Nhân bản 1 trang."""
    new_item = manager.duplicate_page(req.page_id)
    if not new_item:
        raise HTTPException(status_code=404, detail="Không tìm thấy trang để nhân bản.")
    return {"success": True, "pages": manager.list_pages()}


@app.post("/api/pages/clear")
async def clear_pages():
    """Xóa toàn bộ trang trong danh sách."""
    global current_source_pdf
    manager.clear()
    current_source_pdf = None
    return {"success": True, "pages": []}


# ==========================================
# CÁC API HỆ THỐNG TỆP TIN & GHI NHỚ THƯ MỤC
# ==========================================

@app.get("/api/fs/source-info")
async def get_fs_source_info():
    """Lấy thông tin các thư mục nhớ riêng biệt (Open, Add, Save) và tệp PDF nguồn đang mở."""
    from core.fs_manager import get_action_folder
    return {
        "success": True,
        "folder_open": get_action_folder("open"),
        "folder_add": get_action_folder("add"),
        "folder_save": get_action_folder("save"),
        "last_folder": get_action_folder("open"),
        "source_pdf": current_source_pdf,
    }


@app.post("/api/fs/pick-files")
async def pick_files_api(action: str = "open"):
    """Mở hộp thoại Explorer của Windows để chọn tệp tại thư mục nhớ riêng biệt: 'open' hoặc 'add'."""
    from core.fs_manager import pick_files_dialog, read_image_unicode, get_action_folder
    global current_source_pdf

    file_paths = await run_in_threadpool(pick_files_dialog, action=action)
    if not file_paths:
        return {"success": False, "cancelled": True, "pages": manager.list_pages()}

    uploaded_count = 0
    # Nếu chỉ mở 1 file PDF thì ghi nhận nguồn gốc để cho phép lưu trực tiếp
    if len(file_paths) == 1 and file_paths[0].lower().endswith(".pdf"):
        single_pdf = file_paths[0]
        current_source_pdf = {
            "path": single_pdf,
            "name": os.path.basename(single_pdf),
            "folder": os.path.dirname(single_pdf),
        }

    for fpath in file_paths:
        fname = os.path.basename(fpath)
        ext = os.path.splitext(fname)[1].lower()
        try:
            if ext == ".pdf":
                with open(fpath, "rb") as f:
                    pdf_bytes = f.read()
                items = await run_in_threadpool(manager.add_pdf, fname, pdf_bytes)
                uploaded_count += len(items)
            else:
                img = await run_in_threadpool(read_image_unicode, fpath)
                if img is not None:
                    manager.add_image(fname, img)
                    uploaded_count += 1
        except Exception as e:
            print(f"[Warning] Error opening {fpath}: {e}")

    return {
        "success": True,
        "uploaded_count": uploaded_count,
        "pages": manager.list_pages(),
        "source_pdf": current_source_pdf,
        "folder_used": get_action_folder(action),
    }


@app.post("/api/fs/pick-folder")
async def pick_folder_api(action: str = "open"):
    """Mở hộp thoại chọn thư mục của Windows tại đúng thư mục nhớ riêng biệt: 'open' hoặc 'add'."""
    from core.fs_manager import pick_folder_dialog, read_image_unicode, get_action_folder

    folder, file_paths = await run_in_threadpool(pick_folder_dialog, action=action)
    if not folder or not file_paths:
        return {"success": False, "cancelled": True, "pages": manager.list_pages()}

    uploaded_count = 0
    for fpath in file_paths:
        fname = os.path.basename(fpath)
        ext = os.path.splitext(fname)[1].lower()
        try:
            if ext == ".pdf":
                with open(fpath, "rb") as f:
                    pdf_bytes = f.read()
                items = await run_in_threadpool(manager.add_pdf, fname, pdf_bytes)
                uploaded_count += len(items)
            else:
                img = await run_in_threadpool(read_image_unicode, fpath)
                if img is not None:
                    manager.add_image(fname, img)
                    uploaded_count += 1
        except Exception as e:
            print(f"[Warning] Error opening {fpath}: {e}")

    return {
        "success": True,
        "folder": folder,
        "uploaded_count": uploaded_count,
        "pages": manager.list_pages(),
        "folder_used": get_action_folder(action),
    }


@app.post("/api/fs/save-pdf-direct")
async def save_pdf_direct_api(req: SavePdfDirectRequest):
    """Lưu đè trực tiếp vào file PDF gốc đang mở (tự động tạo file backup .bak)."""
    global current_source_pdf
    if not current_source_pdf or not current_source_pdf.get("path"):
        raise HTTPException(status_code=400, detail="Chưa có đường dẫn file PDF gốc trên máy để lưu đè.")

    pdf_path = current_source_pdf["path"]
    pages = await run_in_threadpool(manager.get_ordered_pages)
    if not pages:
        raise HTTPException(status_code=400, detail="Chưa có trang nào để lưu PDF.")

    def _save():
        # Sao lưu an toàn .bak
        if os.path.exists(pdf_path):
            backup_path = f"{pdf_path}.bak"
            try:
                import shutil
                shutil.copy2(pdf_path, backup_path)
            except Exception as e:
                print(f"[Backup warning] {e}")

        pdf_bytes = build_pdf_from_pages(
            pages,
            layout_mode=req.layout_mode,
            quality=req.quality,
            normalize_res=True,
        )
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        from core.fs_manager import set_action_folder
        set_action_folder("save", pdf_path)
        return len(pdf_bytes)

    size_bytes = await run_in_threadpool(_save)
    return {
        "success": True,
        "path": pdf_path,
        "filename": current_source_pdf["name"],
        "folder": current_source_pdf["folder"],
        "size_bytes": size_bytes,
    }


@app.post("/api/fs/save-pdf-as")
async def save_pdf_as_api(req: SavePdfAsRequest):
    """Mở hộp thoại Save As của Windows tại thư mục nhớ gần nhất để lưu PDF trực tiếp vào ổ đĩa."""
    from core.fs_manager import pick_save_pdf_dialog, set_last_folder
    global current_source_pdf

    pages = await run_in_threadpool(manager.get_ordered_pages)
    if not pages:
        raise HTTPException(status_code=400, detail="Chưa có trang nào để lưu PDF.")

    fname = req.suggested_name or (current_source_pdf["name"] if current_source_pdf else "tai_lieu_dong_nhat.pdf")
    chosen_path = await run_in_threadpool(pick_save_pdf_dialog, fname)
    if not chosen_path:
        return {"success": False, "cancelled": True}

    def _save():
        pdf_bytes = build_pdf_from_pages(
            pages,
            layout_mode=req.layout_mode,
            quality=req.quality,
            normalize_res=True,
        )
        with open(chosen_path, "wb") as f:
            f.write(pdf_bytes)

        set_last_folder(chosen_path)
        return len(pdf_bytes)

    size_bytes = await run_in_threadpool(_save)
    current_source_pdf = {
        "path": chosen_path,
        "name": os.path.basename(chosen_path),
        "folder": os.path.dirname(chosen_path),
    }

    return {
        "success": True,
        "path": chosen_path,
        "filename": os.path.basename(chosen_path),
        "folder": os.path.dirname(chosen_path),
        "size_bytes": size_bytes,
    }


# ==========================================
# CÁC API CẤU HÌNH & GỢI Ý TÊN BẰNG AI
# ==========================================

@app.get("/api/config")
async def get_config_info():
    """Lấy thông tin trạng thái cấu hình AI (không để lộ full key)."""
    from core.ai_namer import load_config
    cfg = load_config()
    raw_key = cfg.get("openai_api_key", "").strip()
    has_key = bool(raw_key)
    masked_key = f"{raw_key[:4]}...{raw_key[-4:]}" if len(raw_key) > 8 else ("***" if has_key else "")
    return {
        "success": True,
        "has_openai_key": has_key,
        "masked_key": masked_key,
        "model": cfg.get("openai_model", "gpt-4o-mini"),
    }


@app.post("/api/config")
async def update_config_api(req: ConfigUpdateRequest):
    """Cập nhật ChatGPT API Key hoặc Model vào config.json."""
    from core.ai_namer import save_config
    update_data = {}
    if req.openai_api_key is not None:
        update_data["openai_api_key"] = req.openai_api_key.strip()
    if req.openai_model is not None:
        update_data["openai_model"] = req.openai_model.strip()

    ok = save_config(update_data)
    return {"success": ok}


@app.post("/api/ai/suggest-name")
async def suggest_name_api():
    """Gợi ý tên tệp xuất thông minh bằng AI ChatGPT hoặc OCR phân tích nội dung trang đầu."""
    from core.ai_namer import suggest_document_filename
    pages = manager.list_pages()
    if not pages:
        return {
            "success": True,
            "engine": "default",
            "primary": "tai_lieu_dong_nhat",
            "suggestions": ["tai_lieu_dong_nhat"],
            "message": "Chưa có trang tài liệu."
        }

    first_page = manager.get_page(pages[0]["id"])
    first_img = await run_in_threadpool(first_page.get_processed_image) if first_page else None
    page_names = [p["name"] for p in pages]

    result = await run_in_threadpool(suggest_document_filename, first_img, page_names)
    return result


# ==========================================
# CÁC API ƯỚC LƯỢNG KÍCH THƯỚC & NÉN
# ==========================================

@app.post("/api/estimate-size")
async def estimate_images_size_api(req: EstimateSizeRequest):
    """Ước lượng kích thước tệp và độ phân giải sau khi nén."""
    images = await run_in_threadpool(manager.get_ordered_processed_images, req.page_ids)
    if not images:
        return {"success": True, "total_bytes": 0, "formatted_total": "0 B"}

    result = await run_in_threadpool(
        estimate_images_size,
        images,
        format=req.format,
        quality=req.quality,
        max_long_edge=req.max_dimension,
    )
    return {"success": True, **result}


@app.post("/api/estimate-pdf-size")
async def estimate_pdf_size_api(req: EstimatePdfSizeRequest):
    """Ước lượng dung lượng file PDF khi xuất với khổ đồng nhất và chất lượng đã chọn."""
    images = await run_in_threadpool(manager.get_ordered_processed_images, req.page_ids)
    if not images:
        return {"success": True, "total_bytes": 0, "formatted_total": "0 B"}

    result = await run_in_threadpool(
        estimate_pdf_size,
        images,
        layout_mode=req.layout_mode,
        quality=req.quality,
    )
    return {"success": True, **result}


# ==========================================
# CÁC API XUẤT SẢN PHẨM (OUTPUTS)
# ==========================================

@app.post("/api/export/pdf")
async def export_pdf(req: ExportPdfRequest):
    """Xuất danh sách trang thành 1 file PDF hoàn chỉnh với khung trang và hình ảnh chuẩn."""
    pages = await run_in_threadpool(manager.get_ordered_pages, req.page_ids)
    if not pages:
        raise HTTPException(status_code=400, detail="Không có trang nào để xuất PDF.")

    def _build():
        return build_pdf_from_pages(
            pages,
            layout_mode=req.layout_mode,
            quality=req.quality,
            normalize_res=True,
        )

    pdf_bytes = await run_in_threadpool(_build)

    filename = req.filename or "tai_lieu_dong_nhat.pdf"
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    ascii_fname = urllib.parse.quote(filename)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"{ascii_fname}\"; filename*=UTF-8''{ascii_fname}",
            "Cache-Control": "no-store",
        },
    )


@app.post("/api/export/stitch-preview")
async def stitch_preview(req: StitchPreviewRequest):
    """Tạo nhanh ảnh xem trước ghép 1 ảnh (Dọc, Grid nhiều cột, Ngang)."""
    images = await run_in_threadpool(manager.get_ordered_processed_images, req.page_ids)
    if not images:
        raise HTTPException(status_code=400, detail="Không có trang nào để ghép ảnh.")

    def _process():
        c_bgr = parse_color_hex(req.bg_color, (255, 255, 255))
        stitched = stitch_images(
            images,
            layout=req.layout,
            cols=req.cols,
            spacing=req.spacing,
            padding=req.padding,
            bg_color=c_bgr,
            draw_border=req.draw_border,
            last_row_align=req.last_row_align,
            scale=req.scale,
            max_total_dim=8000,
        )
        sh, sw = stitched.shape[:2]
        preview_bytes = make_stitched_preview(stitched, max_preview_dim=1600, quality=80)
        return preview_bytes, sw, sh, len(images)

    preview_bytes, sw, sh, num_pages = await run_in_threadpool(_process)

    return Response(
        content=preview_bytes,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store",
            "X-Out-Width": str(sw),
            "X-Out-Height": str(sh),
            "X-Page-Count": str(num_pages),
        },
    )


@app.post("/api/export/stitch-download")
async def stitch_download(req: StitchDownloadRequest):
    """Tải về ảnh ghép chất lượng cao đầy đủ độ phân giải."""
    images = await run_in_threadpool(manager.get_ordered_processed_images, req.page_ids)
    if not images:
        raise HTTPException(status_code=400, detail="Không có trang nào để ghép ảnh.")

    def _process():
        c_bgr = parse_color_hex(req.bg_color, (255, 255, 255))
        stitched = stitch_images(
            images,
            layout=req.layout,
            cols=req.cols,
            spacing=req.spacing,
            padding=req.padding,
            bg_color=c_bgr,
            draw_border=req.draw_border,
            last_row_align=req.last_row_align,
            scale=req.scale,
        )
        data, mime = encode_stitched_image(stitched, format=req.format, quality=req.quality)
        return data, mime, stitched.shape[1], stitched.shape[0]

    data, mime, sw, sh = await run_in_threadpool(_process)

    ext = "png" if (req.format or "").lower() == "png" else "jpg"
    filename = req.filename or f"anh_ghep_{len(images)}_trang.{ext}"
    if not filename.lower().endswith(f".{ext}"):
        filename += f".{ext}"
    ascii_fname = urllib.parse.quote(filename)

    return Response(
        content=data,
        media_type=mime,
        headers={
            "Content-Disposition": f"attachment; filename=\"{ascii_fname}\"; filename*=UTF-8''{ascii_fname}",
            "X-Out-Width": str(sw),
            "X-Out-Height": str(sh),
        },
    )


@app.post("/api/export/images-zip")
async def export_images_zip(req: ExportZipRequest):
    """Tải về toàn bộ các trang đã nén và chỉnh sửa theo thứ tự thành 1 tệp ZIP."""
    images = await run_in_threadpool(manager.get_ordered_processed_images, req.page_ids)
    if not images:
        raise HTTPException(status_code=400, detail="Không có trang nào để xuất file ZIP.")

    fmt = (req.format or "jpeg").lower()
    ext = "png" if fmt == "png" else ("webp" if fmt == "webp" else "jpg")

    def _make_zip():
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, img in enumerate(images):
                img_bytes, _ = compress_image_to_bytes(
                    img,
                    format=fmt,
                    quality=req.quality,
                    max_long_edge=req.max_dimension,
                )
                zf.writestr(f"trang_{idx + 1:03d}.{ext}", img_bytes)
        return zip_buf.getvalue()

    zip_bytes = await run_in_threadpool(_make_zip)

    filename = req.filename or "danh_sach_anh.zip"
    if not filename.lower().endswith(".zip"):
        filename += ".zip"
    ascii_fname = urllib.parse.quote(filename)

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=\"{ascii_fname}\"; filename*=UTF-8''{ascii_fname}",
        },
    )


@app.get("/api/export/single/{page_id}")
async def export_single_page(page_id: str, format: str = "jpeg", quality: int = 90, max_dimension: Optional[int] = None):
    """Tải về riêng 1 trang đơn lẻ dạng ảnh với nén tùy chỉnh."""
    page = manager.get_page(page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Không tìm thấy trang yêu cầu.")

    img = await run_in_threadpool(page.get_processed_image)
    data, mime = compress_image_to_bytes(img, format=format, quality=quality, max_long_edge=max_dimension)
    ext = "png" if format.lower() == "png" else ("webp" if format.lower() == "webp" else "jpg")
    filename = f"{page.name}.{ext}"
    ascii_fname = urllib.parse.quote(filename)

    return Response(
        content=data,
        media_type=mime,
        headers={
            "Content-Disposition": f"attachment; filename=\"{ascii_fname}\"; filename*=UTF-8''{ascii_fname}",
        },
    )


# ==========================================
# PHỤC VỤ GIAO DIỆN WEB TĨNH
# ==========================================

@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
