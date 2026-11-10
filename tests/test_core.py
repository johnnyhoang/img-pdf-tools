import os
import sys
import numpy as np
import cv2
import fitz

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Thêm đường dẫn thư mục gốc vào sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.enhancer import enhance_document, rotate_image
from core.pdf_engine import (
    build_pdf_from_images,
    render_pdf_to_images,
    estimate_images_size,
    estimate_pdf_size,
    compress_image_to_bytes,
)
from core.pdf_stitcher import stitch_images, encode_stitched_image, make_stitched_preview
from core.pagemanager import PageManager


def test_core_flow():
    print("1. Kiểm tra PageManager & tạo các trang với kích thước giống ảnh của người dùng...")
    pm = PageManager()

    # Trang 1 & 2: Kích thước cao 1820 x 2596 px (như ảnh người dùng gửi)
    img1 = np.full((2596, 1820, 3), (255, 255, 255), dtype=np.uint8)
    cv2.putText(img1, "Page 1 - 1820x2596", (100, 1000), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 255), 4)

    img2 = np.full((2596, 1820, 3), (245, 245, 245), dtype=np.uint8)
    cv2.putText(img2, "Page 2 - 1820x2596", (100, 1000), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 180, 0), 4)

    # Trang 3, 4, 5: Kích thước 1700 x 2200 px
    img3 = np.full((2200, 1700, 3), (250, 250, 250), dtype=np.uint8)
    cv2.putText(img3, "Page 3 - 1700x2200", (100, 1000), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 0, 0), 4)

    p1 = pm.add_image("birth_cert_minh_anh_vn_1.jpg", img1)
    p2 = pm.add_image("birth_cert_minh_anh_vn_2.jpg", img2)
    p3 = pm.add_image("Giay_Khai_Sinh_3.jpg", img3)

    pages = pm.list_pages()
    assert len(pages) == 3
    print(f"   -> Đã nạp 3 trang: Trang 1 ({pages[0]['width']}x{pages[0]['height']}), Trang 3 ({pages[2]['width']}x{pages[2]['height']})")

    print("2. Kiểm tra phát hiện khổ ảnh mẫu (Distinct Dimensions)...")
    dims = pm.get_distinct_dimensions()
    assert len(dims) == 2
    print(f"   -> Các khổ ảnh hiện có: {[d['label'] for d in dims]}")

    print("3. Kiểm tra chỉnh riêng Trang 1 & Trang 2 về 1700 x 2200 px...")
    # Chỉnh trang 1 về 1700 x 2200 với crop_to_fit (cắt bớt phần cao thừa)
    ok1 = pm.resize_page(p1.id, 1700, 2200, fit_mode="crop_to_fit")
    assert ok1
    p1_info = pm.get_page(p1.id).to_dict(0)
    assert p1_info["image_width"] == 1700 and p1_info["image_height"] == 2200, f"Ảnh Trang 1 phải là 1700x2200, nhận {p1_info['image_width']}x{p1_info['image_height']}"
    assert p1_info["width"] == 1654 and p1_info["height"] == 2339, f"Khổ trang phải là A4 (1654x2339), nhận {p1_info['width']}x{p1_info['height']}"
    print(f"   -> Trang 1: Khổ trang {p1_info['width']}x{p1_info['height']} px, Hình ảnh {p1_info['image_width']} × {p1_info['image_height']} px!")

    # Chỉnh trang 2 về chiều rộng 1700 px (giữ tỷ lệ chiều cao)
    ok2 = pm.resize_page(p2.id, 1700, fit_mode="proportional_w")
    assert ok2
    p2_info = pm.get_page(p2.id).to_dict(1)
    assert p2_info["image_width"] == 1700
    print(f"   -> Trang 2: Hình ảnh đã đổi thành công về: {p2_info['image_width']} × {p2_info['image_height']} px (rộng 1700px giữ tỷ lệ)!")

    print("4. Kiểm tra cắt lề thủ công (Crop margins)...")
    ok3 = pm.crop_page_margins(p1.id, top=50, bottom=50, left=20, right=20)
    assert ok3
    p1_cropped = pm.get_page(p1.id).to_dict(0)
    assert p1_cropped["image_width"] == 1700 - 40 and p1_cropped["image_height"] == 2200 - 100
    print(f"   -> Cắt lề thành công: {p1_cropped['image_width']} × {p1_cropped['image_height']} px")

    print("5. Kiểm tra khôi phục ảnh gốc (Reset)...")
    pm.reset_page(p1.id)
    p1_reset = pm.get_page(p1.id).to_dict(0)
    assert p1_reset["image_width"] == 1820 and p1_reset["image_height"] == 2596
    print(f"   -> Khôi phục ảnh gốc thành công: {p1_reset['image_width']} × {p1_reset['image_height']} px")

    print("6. Kiểm tra AI gợi ý tên file tự động...")
    from core.ai_namer import suggest_document_filename
    sug_res = suggest_document_filename(img1, ["Giay_Khai_Sinh_Minh_Anh.jpg"])
    assert sug_res["success"] is True
    assert len(sug_res["suggestions"]) > 0
    print(f"   -> Gợi ý tên thành công: '{sug_res['primary']}', các lựa chọn: {sug_res['suggestions']}")

    print("7. Kiểm tra xuất PDF giữ nguyên kích thước gốc (không tự resize fill tràn page)...")
    # Tạo 1 ảnh nhỏ 800 x 600 px và 1 ảnh 1700 x 2200 px
    small_img = np.full((600, 800, 3), (255, 255, 255), dtype=np.uint8)
    pdf_bytes_orig = build_pdf_from_images([small_img, img3], layout_mode="original")
    doc_test = fitz.open(stream=pdf_bytes_orig, filetype="pdf")
    assert len(doc_test) == 2
    # Trang 1: Phải có kích thước đúng 800 * 72 / 200 = 288 pt x 216 pt (không bị ép thành 595 pt A4)
    p0_w, p0_h = round(doc_test[0].rect.width), round(doc_test[0].rect.height)
    assert p0_w == 288 and p0_h == 216, f"Trang 1 phải giữ nguyên kích thước 288x216 pt, nhận {p0_w}x{p0_h}"
    print(f"   -> Trang 1 giữ nguyên kích thước chuẩn ảnh: {p0_w} × {p0_h} pt (không bị resize fill page)!")
    doc_test.close()

    print("8. Kiểm tra tách bạch KHUNG TRANG (Page Canvas A4) & ĐỐI TƯỢNG HÌNH ẢNH (Image Object)...")
    # Đặt Trang 1 lên Khung giấy A4 Dọc, hình ảnh scale 50%, đặt ở nửa trên trang (như photo Hộ chiếu/CCCD)
    pm.setup_pages([p1.id], page_size="A4", orientation="portrait", placement="top", scale=0.5)
    p1_a4 = pm.get_page(p1.id).to_dict(0)
    assert p1_a4["page_size"] == "A4"
    assert p1_a4["width"] == 1654 and p1_a4["height"] == 2339, "Khung trang phải là A4 Dọc (1654 x 2339 px)"
    assert p1_a4["image_width"] == 1820 and p1_a4["image_height"] == 2596, "Kích thước hình ảnh gốc phải được giữ nguyên"
    assert p1_a4["image_scale"] == 0.5 and p1_a4["image_placement"] == "top"
    print(f"   -> Trang 1: Khung giấy A4 ({p1_a4['width']}x{p1_a4['height']} px), Hình ({p1_a4['image_width']}x{p1_a4['image_height']} px @ 50%), Vị trí: Nửa trên!")

    # Xuất PDF với Trang 1 là A4
    from core.pdf_engine import build_pdf_from_pages
    pdf_pages = pm.get_ordered_pages([p1.id])
    pdf_bytes_a4 = build_pdf_from_pages(pdf_pages)
    doc_a4 = fitz.open(stream=pdf_bytes_a4, filetype="pdf")
    rect_a4 = doc_a4[0].rect
    assert round(rect_a4.width) == 595 and round(rect_a4.height) == 842, "PDF Page phải là A4 chuẩn 595 x 842 pt"
    print(f"   -> Xuất PDF: Khổ trang đúng chuẩn A4 ({round(rect_a4.width)} × {round(rect_a4.height)} pt), hình ảnh đặt đúng tỷ lệ!")
    doc_a4.close()

    print("9. Kiểm tra KHỔ TRANG TOÀN BỘ FILE (Document-Level Page Setup)...")
    pm.set_document_page_size("A4", "portrait")
    all_pages = pm.list_pages()
    for p in all_pages:
        assert p["page_size"] == "A4" and p["orientation"] == "portrait"
    print("   -> Đã chuyển toàn bộ tài liệu sang A4 Dọc đồng nhất thành công!")

    pm.set_document_page_size("fit_image")
    all_pages_fit = pm.list_pages()
    for p in all_pages_fit:
        assert p["page_size"] == "fit_image"
    print("   -> Đã chuyển toàn bộ tài liệu về Vừa khít ảnh thành công!")

    print("10. Kiểm tra CHẤM GÓC (4 điểm & 6 điểm), XOAY, CHỈNH MÀU SÁNG TỐI...")
    from core.detector import detect_document_corners, four_point_transform, expand_quad
    # Tạo 1 ảnh mô phỏng tài liệu có góc lệch
    doc_canvas = np.full((1000, 800, 3), 40, dtype=np.uint8) # Nền tối
    # Vẽ tờ giấy trắng nghiêng ở giữa
    paper_pts = np.array([[100, 80], [700, 120], [680, 900], [120, 850]], dtype=np.int32)
    cv2.fillPoly(doc_canvas, [paper_pts], (240, 240, 240))
    p_doc = pm.add_image("test_skewed_doc.jpg", doc_canvas)

    # Tự động nhận diện góc
    corners_detected, is_found = detect_document_corners(doc_canvas)
    assert len(corners_detected) == 4
    print(f"   -> Nhận diện góc thành công ({is_found}): 4 điểm chuẩn!")

    # Áp dụng nắn 4 góc + xoay 90 độ + tăng sáng 20% + tăng tương phản 30%
    p_doc_item = pm.get_page(p_doc.id)
    p_doc_item.apply_full_edit(
        corners=corners_detected.tolist(),
        rotation=90,
        brightness=0.2,
        contrast=0.3,
        filter_mode="clean_bg"
    )
    p_doc_info = p_doc_item.to_dict(3)
    assert p_doc_info["rotation"] == 90
    assert p_doc_info["brightness"] == 0.2
    assert p_doc_info["contrast"] == 0.3
    assert p_doc_info["filter_mode"] == "clean_bg"
    assert p_doc_info["is_modified"] is True
    print(f"   -> Nắn thẳng 4 góc & xoay 90° & chỉnh sáng tối thành công: {p_doc_info['image_width']}x{p_doc_info['image_height']} px!")

    # Kiểm tra nắn 6 điểm (Hộ chiếu / Sách mở đôi)
    pts_6 = [
        [50, 50], [400, 60], [750, 50],
        [750, 950], [400, 940], [50, 950]
    ]
    p_doc_item.apply_full_edit(corners=pts_6)
    p_doc_6_info = p_doc_item.to_dict(3)
    assert len(p_doc_6_info["corners"]) == 6
    print(f"   -> Nắn 6 điểm (Sách / Hộ chiếu mở đôi) thành công: {p_doc_6_info['image_width']}x{p_doc_6_info['image_height']} px!")

    # Khôi phục gốc
    p_doc_item.reset_to_original()
    p_reset_info = p_doc_item.to_dict(3)
    assert p_reset_info["corners"] is None
    assert p_reset_info["rotation"] == 0
    assert p_reset_info["brightness"] == 0.0
    print("   -> Khôi phục ảnh gốc ban đầu thành công!")

    print("11. Kiểm tra preset Passport 2 mặt (1386 x 1005 px) không bị scale nhân đôi hay ép full trang...")
    p_pass = pm.add_image("passport_double_test.jpg", np.full((1000, 1200, 3), 200, dtype=np.uint8))
    p_pass_item = pm.get_page(p_pass.id)
    # Khổ trang chuẩn A4 Dọc (1654 x 2339)
    p_pass_item.setup_page_canvas(page_size="A4", orientation="portrait", placement="center")
    # Áp dụng preset kích thước Passport 2 mặt
    p_pass_item.apply_full_edit(target_w=1386, target_h=1005, image_scale=1.16)
    p_pass_info = p_pass_item.to_dict(4)
    # 1. Kích thước hình ảnh phải đúng 1386 x 1005 px
    assert p_pass_info["image_width"] == 1386 and p_pass_info["image_height"] == 1005, f"Lỗi kích thước ảnh: {p_pass_info['image_width']}x{p_pass_info['image_height']}"
    # 2. image_scale phải được reset về 1.0 (100%), không được lưu 1.16 gây nhân đôi
    assert p_pass_info["image_scale"] == 1.0 and p_pass_info["image_scale_pct"] == 100, f"Lỗi scale factor: {p_pass_info['image_scale']}"
    # 3. Canvas A4 phải có kích thước 1654 x 2339 và ảnh phải chiếm đúng 1386 px chiều ngang (không ép full 1654 px)
    canvas_img = p_pass_item.get_processed_image()
    assert canvas_img.shape[0] == 2339 and canvas_img.shape[1] == 1654
    # Biên trái phải là (1654 - 1386) // 2 = 134 px viền trắng
    assert np.all(canvas_img[1000, :130] == 255), "Lề trái trên trang A4 phải là nền trắng, không bị tràn mép"
    assert np.all(canvas_img[1000, 1654 - 130:] == 255), "Lề phải trên trang A4 phải là nền trắng, không bị tràn mép"
    print(f"   -> Preset Passport 2 mặt chuẩn xác: Hình {p_pass_info['image_width']}x{p_pass_info['image_height']} px (scale={p_pass_info['image_scale']}), lọt gọn trên canvas A4 {canvas_img.shape[1]}x{canvas_img.shape[0]} px!")

    print("12. Kiểm tra khổ US Letter (Fill & Fit) và xuất PDF...")
    img_letter_src = np.full((1200, 1000, 3), (120, 150, 180), dtype=np.uint8)
    p_let = pm.add_image("test_us_letter.jpg", img_letter_src)
    p_let_item = pm.get_page(p_let.id)

    # 12.1. Letter Fill
    p_let_item.setup_page_canvas(page_size="letter", orientation="portrait", placement="fill")
    let_fill_canvas = p_let_item.get_processed_image()
    assert let_fill_canvas.shape == (2200, 1700, 3), f"Khổ canvas Letter Dọc phải là (2200, 1700, 3), nhận: {let_fill_canvas.shape}"
    # Vì là placement="fill", 4 góc của tờ giấy phải được lấp đầy hoàn toàn bằng màu ảnh (120, 150, 180), không bị viền trắng (255, 255, 255)
    assert np.all(let_fill_canvas[0, 0] == (120, 150, 180)), "Góc trên-trái phải được phủ kín không viền trắng"
    assert np.all(let_fill_canvas[2199, 1699] == (120, 150, 180)), "Góc dưới-phải phải được phủ kín không viền trắng"
    print("   -> Letter Fill: Hình ảnh đã phóng to lấp đầy hoàn toàn trang Letter 1700x2200 px không còn viền trắng!")

    # 12.2. Letter Fit
    p_let_item.setup_page_canvas(page_size="letter", orientation="portrait", placement="fit")
    let_fit_canvas = p_let_item.get_processed_image()
    assert let_fit_canvas.shape == (2200, 1700, 3)
    # Vì ảnh 1000x1200 (tỷ lệ 0.833) thon ngang hơn khổ Letter 1700x2200 (0.772), nên fit chiều cao 2200px -> rộng 1833px tràn mép hoặc fit chiều rộng 1700px -> cao 2040px chừa lề trắng trên dưới
    # Với 1000x1200: min(1700/1000, 2200/1200) = min(1.7, 1.833) = 1.7
    # Width = 1700, Height = 2040 -> lề trên y = (2200 - 2040) // 2 = 80px lề trắng
    assert np.all(let_fit_canvas[10, 850] == (255, 255, 255)), "Phần lề trên phải là màu trắng của trang giấy"
    print("   -> Letter Fit: Hình ảnh co vừa vặn trong khổ Letter 1700x2200 px!")

    # 12.3. Xuất PDF khổ Letter
    pdf_bytes = build_pdf_from_pages([p_let_item], layout_mode="uniform_letter_portrait")
    doc_check = fitz.open(stream=pdf_bytes, filetype="pdf")
    assert len(doc_check) == 1
    pdf_p = doc_check[0]
    assert round(pdf_p.rect.width) == 612 and round(pdf_p.rect.height) == 792, f"Kích thước PDF Letter phải là 612x792 pt, nhận {pdf_p.rect}"
    doc_check.close()
    print("   -> Xuất PDF: Chuẩn khổ US Letter 612 x 792 pt (8.5 x 11 inches)!")

    print("\n===> TẤT CẢ CÁC KIỂM TRA ĐỀU THÀNH CÔNG RỰC RỠ! <===")


if __name__ == "__main__":
    test_core_flow()
