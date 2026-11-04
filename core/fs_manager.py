import os
import shutil
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import cv2

from .ai_namer import load_config, save_config


def get_action_folder(action: str = "open") -> str:
    """
    Lấy thư mục nhớ RIÊNG BIỆT theo hành động:
    - 'open': Thư mục mở file / mở PDF ban đầu (folder_open)
    - 'add': Thư mục thêm tệp / thêm ảnh bổ sung (folder_add)
    - 'save': Thư mục tải xuống / lưu file PDF/ZIP (folder_save)
    """
    cfg = load_config()
    key_map = {
        "open": "folder_open",
        "add": "folder_add",
        "save": "folder_save",
    }
    key = key_map.get(action, "folder_open")
    folder = cfg.get(key, "").strip()
    if folder and os.path.isdir(folder):
        return os.path.normpath(folder)

    # Nếu key riêng chưa có, fallback sang last_folder cũ
    last = cfg.get("last_folder", "").strip()
    if last and os.path.isdir(last):
        return os.path.normpath(last)

    # Thư mục Documents mặc định của Windows
    docs = os.path.join(os.path.expanduser("~"), "Documents")
    if os.path.isdir(docs):
        return os.path.normpath(docs)
    return os.path.normpath(os.path.expanduser("~"))


def set_action_folder(action: str, path_or_dir: str):
    """
    Ghi nhớ thư mục RIÊNG BIỆT theo từng hành động:
    - 'open' -> folder_open
    - 'add'  -> folder_add
    - 'save' -> folder_save
    """
    if not path_or_dir:
        return
    folder = path_or_dir if os.path.isdir(path_or_dir) else os.path.dirname(path_or_dir)
    if folder and os.path.isdir(folder):
        norm = os.path.normpath(folder)
        key_map = {
            "open": "folder_open",
            "add": "folder_add",
            "save": "folder_save",
        }
        key = key_map.get(action, "folder_open")
        save_config({key: norm, "last_folder": norm})


def get_last_folder() -> str:
    """Tương thích ngược: lấy folder_open hoặc last_folder."""
    return get_action_folder("open")


def set_last_folder(path_or_dir: str):
    """Tương thích ngược: lưu vào folder_open."""
    set_action_folder("open", path_or_dir)


def pick_files_dialog(action: str = "open") -> List[str]:
    """
    Mở hộp thoại Explorer của Windows để chọn tệp:
    - action='open': nhớ thư mục Open riêng
    - action='add': nhớ thư mục Thêm tệp riêng
    """
    import tkinter as tk
    from tkinter import filedialog

    init_dir = get_action_folder(action)
    title_text = "Mở tệp PDF hoặc ảnh" if action == "open" else "Chọn thêm ảnh hoặc file PDF vào tài liệu"

    win = tk.Tk()
    win.withdraw()
    win.attributes("-topmost", True)
    try:
        chosen = filedialog.askopenfilenames(
            title=title_text,
            initialdir=init_dir,
            filetypes=[
                ("Ảnh & Tài liệu PDF", "*.pdf;*.jpg;*.jpeg;*.png;*.webp;*.bmp;*.tiff"),
                ("Tài liệu PDF (*.pdf)", "*.pdf"),
                ("Tệp hình ảnh (*.jpg;*.png;...)", "*.jpg;*.jpeg;*.png;*.webp;*.bmp"),
                ("Tất cả tệp", "*.*"),
            ]
        )
    finally:
        win.destroy()

    if chosen:
        file_list = [os.path.normpath(p) for p in chosen]
        set_action_folder(action, file_list[0])
        return file_list
    return []


def pick_folder_dialog(action: str = "open") -> Tuple[str, List[str]]:
    """
    Mở hộp thoại chọn thư mục của Windows:
    - action='open': nhớ thư mục Open riêng
    - action='add': nhớ thư mục Thêm tệp riêng
    """
    import tkinter as tk
    from tkinter import filedialog

    init_dir = get_action_folder(action)
    win = tk.Tk()
    win.withdraw()
    win.attributes("-topmost", True)
    try:
        chosen = filedialog.askdirectory(
            title="Chọn thư mục chứa ảnh hoặc PDF",
            initialdir=init_dir
        )
    finally:
        win.destroy()

    if chosen and os.path.isdir(chosen):
        folder = os.path.normpath(chosen)
        set_action_folder(action, folder)
        supported = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
        matched = []
        for entry in sorted(os.listdir(folder)):
            ext = os.path.splitext(entry)[1].lower()
            if ext in supported:
                matched.append(os.path.join(folder, entry))
        return folder, matched
    return "", []


def pick_save_pdf_dialog(suggested_name: str = "tai_lieu_dong_nhat.pdf") -> str:
    """
    Mở hộp thoại Lưu PDF (Save As) của Windows:
    - Nhớ thư mục TẢI XUỐNG / LƯU (folder_save) HOÀN TOÀN RIÊNG BIỆT.
    """
    import tkinter as tk
    from tkinter import filedialog

    init_dir = get_action_folder("save")
    if not suggested_name.lower().endswith(".pdf"):
        suggested_name += ".pdf"

    win = tk.Tk()
    win.withdraw()
    win.attributes("-topmost", True)
    try:
        chosen = filedialog.asksaveasfilename(
            title="Lưu file PDF vào thư mục (Tải xuống)",
            initialdir=init_dir,
            initialfile=suggested_name,
            defaultextension=".pdf",
            filetypes=[("Tài liệu PDF (*.pdf)", "*.pdf"), ("Tất cả tệp", "*.*")]
        )
    finally:
        win.destroy()

    if chosen:
        chosen_path = os.path.normpath(chosen)
        if not chosen_path.lower().endswith(".pdf"):
            chosen_path += ".pdf"
        set_action_folder("save", chosen_path)
        return chosen_path
    return ""


def read_image_unicode(file_path: str) -> Optional[np.ndarray]:
    """Đọc ảnh an toàn hỗ trợ đầy đủ tiếng Việt và đường dẫn Windows."""
    try:
        data = np.fromfile(file_path, dtype=np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"[Warning] Failed to read image {file_path}: {e}")
        return None
