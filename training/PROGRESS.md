# Tiến độ ngày 04/11/2026

## Đã hoàn thành

- Tạo môi trường training độc lập: PyTorch 2.11.0 + CUDA 12.8; RTX 3060 Laptop 6 GiB chạy backward thành công.
- Tải annotation LVIS chính thức, ghi URL và SHA-256 nguồn; đối chiếu danh mục Open Images.
- Lập danh mục ban đầu 1.000 lớp có dữ liệu, tên không trùng; có bảng `catalog-review.md` để rà soát mức phù hợp với từ cơ bản.
- Chuẩn bị 1.757 ảnh pilot: 983 train / 432 validation / 342 test. Tất cả ảnh hợp lệ; không trùng nội dung giữa các split theo SHA-256.
- Chạy đủ 2 epoch pilot trên GPU và đánh giá 432 ảnh validation bằng LVIS evaluator chính thức.
- Checkpoint pilot nạp được bằng loader YOLO chuẩn trong cả môi trường training lẫn môi trường backend; không phụ thuộc module training tùy biến.
- 9 kiểm thử qua: box/clipping, tách split, annotation chưa xác minh, gradient/loss, detector 1.000 lớp, bounded inference, official evaluator và so sánh đúng cùng manifest/lớp. `pip check` không phát hiện dependency lỗi.

## Chất lượng hiện tại

Pilot chỉ dùng để kiểm tra quy trình. Trên 41 lớp cũ có ánh xạ nghĩa rõ ràng và ground truth trong cùng 432 ảnh:

| Model | AP50–95 trung bình trên 41 lớp chung |
|---|---:|
| Model cũ của backend | 0,1753 |
| Pilot mới, 2 epoch | 0,0329 |

Đây là chỉ số AP trong khoảng 0–1, không phải phần trăm ảnh nhận đúng. Pilot chưa tốt hơn model cũ; chưa thay model ứng dụng. Không so sánh mAP tổng giữa model 51 lớp và model 1.000 lớp như cùng một bài toán.

Bộ đánh giá từng gặp lỗi vì Ultralytics coi danh sách ảnh Python là một batch lớn dù đã chỉ định batch=1. Đã sửa thành chấm từng ảnh, thêm kiểm thử hồi quy và chạy lại thành công. Các log cũ được giữ lại để kiểm tra; trạng thái cuối của job pilot là completed.

## Job dài đang chạy

Tên: `candidate-1000-20261104`.

- Manifest đã chọn 21.507 ảnh train / 3.296 validation / 1.390 test; có 415.840 bounding box trong train.
- Job nền tải và kiểm tra toàn bộ ảnh được chọn, sau đó fine-tune tối đa 100 epoch, có early stopping và checkpoint để resume.
- Điều kiện kỹ thuật trước khi train: job pilot phải hoàn thành huấn luyện và đánh giá. Điều kiện này đã đạt.
- Kết quả cuối được xuất sang `reports/candidate-1000-20261104-val/`; không tự triển khai vào backend.
- Đã thêm `assess.py` để chấm baseline cũ trên cùng bộ validation lớn và so sánh các lớp tương đương. Job nền đang chạy khởi động trước khi thêm bước này; cần chạy assess sau khi job hoàn tất.
- Người dùng đã đồng ý rõ bật theo dõi tự động mỗi 15 phút để kiểm tra job, sửa lỗi/tiếp tục training và đánh giá. Đã tạo heartbeat ACTIVE trong chat này: `theo-d-i-training-model-1-000-nh-n`, tên “Theo dõi training model 1.000 nhãn”. Theo dõi giữ im lặng khi không có thay đổi đáng kể và chạy assess sau khi job hiện hành hoàn tất. Không tạo lịch trùng.
- Xem trạng thái thực tế trong `runs/job-candidate-1000-20261104/status.json` và tiến độ tải trong `prepare.log` cùng thư mục, hoặc chạy `python training/status.py`.

## Dữ liệu cần bổ sung

Tám khái niệm cũ chưa có liên kết dữ liệu LVIS đủ rõ: earbuds, charging case, headphones, tablet, phone, game controller, board, pomegranate. Không gộp nhầm tai nghe chụp tai với mọi loại earphone hoặc board với mọi loại bảng.

Một số lớp LVIS hiếm thiếu mẫu train và thiếu ground truth val/test. Cụ thể profile lớn có 118 lớp chưa có mẫu validation, 274 lớp chưa có mẫu test. Báo cáo sẽ đánh dấu thiếu bằng chứng; chưa thể tuyên bố nhận diện tốt cả 1.000 lớp. Cần bổ sung dữ liệu và ảnh điện thoại độc lập trước khi nghiệm thu.

Model cũ và mã backend/frontend đang dùng được giữ nguyên. Các thay đổi trò chơi đã có sẵn trước phiên training không thuộc công việc này.
