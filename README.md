# 📸 PDF & Image Studio (Lắp Ghép & Chuyển Đổi Vào Ra Image - PDF)

Ứng dụng độc lập chuyên biệt giúp **lắp ghép, sắp xếp và chuyển đổi linh hoạt hai chiều giữa Image và PDF**, tập trung vào việc tạo ra sản phẩm cuối cùng là **các file ảnh đã chỉnh sửa** hoặc **file PDF chuẩn với các trang ảnh theo đúng thứ tự mong muốn**.

---

## 🌟 Tính Năng Nổi Bật

### 1. Đầu Vào Linh Hoạt (Inputs)
- **Nạp nhiều ảnh cùng lúc**: Hỗ trợ JPG, PNG, WEBP, BMP, TIFF...
- **Nạp file PDF**: Tự động giải nén và trích xuất từng trang PDF thành các ảnh độ phân giải cao (sử dụng PyMuPDF).
- **Hỗ trợ kéo & thả (Drag & Drop)** trực tiếp từ màn hình máy tính vào ứng dụng.
- Cho phép thêm tệp tin bất kỳ lúc nào để bổ sung trang vào dự án.

### 2. Không Gian Lắp Ghép & Sắp Xếp Trang (Page Workbench)
- **Kéo thả đổi thứ tự trang**: Sắp xếp lại thứ tự các trang cực kỳ trực quan.
- **Nút di chuyển nhanh**: Chuyển trang lên trước hoặc về sau, đảo ngược toàn bộ danh sách trang.
- **Xoay linh hoạt**: Xoay 90° theo chiều kim đồng hồ cho từng trang hoặc toàn bộ các trang đã chọn.
- **Nhân bản & Xóa**: Nhân bản trang hoặc xóa nhanh trang không cần thiết.
- **Bộ lọc tăng cường tài liệu (Document Enhancer)**:
  - *Làm nét văn bản (Sharp Text)*
  - *Làm trắng sạch nền giấy (Clean Background)*
  - *Quét đen trắng văn phòng (B&W Scan)*
  - *Màu tươi sáng (Magic Color)*
  - *Nổi bật con dấu đỏ & chữ ký xanh (Stamp & Signature Boost)*
  - *Khử ố vàng giấy cũ (Restore Aged Paper)*
  - *Khử mực thấm ngược mặt sau (Remove Bleed-through)*
- **Xem phóng to (Lightbox Preview)**: Nhấp vào bất kỳ trang nào để xem chi tiết độ nét cao.

### 3. Đầu Ra Tinh Gọn & Đa Dạng (Outputs)
- **Xuất File PDF Hoàn Chỉnh**:
  - Ghép tất cả các trang theo đúng thứ tự bạn đã sắp xếp.
  - Tùy chọn khổ giấy: *A4 Thông minh (tự xoay theo ảnh)*, *Vừa khít ảnh 100% (không viền thừa)*, *A4 Dọc cố định*, *A4 Ngang cố định*.
  - Tùy chọn chất lượng bản in (300 DPI siêu nét hoặc 150 DPI cân bằng nhẹ).
- **Ghép 1 Ảnh Duy Nhất (PDF & Image Stitcher)**:
  - Ghép toàn bộ các trang thành 1 bức ảnh dài hoặc ảnh lưới (Grid N cột) hoặc hàng ngang.
  - Tùy chỉnh khoảng cách (spacing), lề (padding), màu nền (trắng/xám/đen), viền mỏng quanh trang.
  - Khung **Live Preview trực quan** hiển thị ngay kết quả.
  - Tải về ảnh JPG/PNG hoặc Sao chép trực tiếp vào bộ nhớ tạm (Clipboard).
- **Xuất Danh Sách Ảnh Đã Xử Lý (ZIP)**:
  - Đóng gói toàn bộ các trang thành file ZIP.
  - Đánh số thứ tự chuẩn đẹp (`trang_001.jpg`, `trang_002.jpg`...).

---

## 🚀 Hướng Dẫn Khởi Động

### Cách 1: Chạy bằng file `run.bat` (Khuyên dùng trên Windows)
- Nhấp đúp chuột vào file **`run.bat`**.
- Ứng dụng sẽ tự động khởi động máy chủ tại cổng `8005` và mở trình duyệt mặc định.

### Cách 2: Chạy bằng dòng lệnh Python
```bash
cd "D:\Hoa Hoang\DeskApps\pdf_image"
python main.py
```
Truy cập trình duyệt tại địa chỉ: `http://127.0.0.1:8005`
