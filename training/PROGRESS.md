# Tiến độ ngày 04/11/2026

## Chuyển sang Colab theo yêu cầu mới

Người dùng không muốn train trên máy nữa và đã chọn **YOLOv8n: tạo run mới, tận dụng model v8n cũ**. Đã chuẩn bị `train_yolov8n_colab.ipynb`, runner `colab_run.py`, hướng dẫn `COLAB.md` và gói `exports/colab-training-v8n.zip` cùng JSON SHA-256. Gói khoảng 4,67 GB, chứa đủ 26.193 ảnh và nhãn, manifest, mã trainer LVIS, model v8n cũ và dữ liệu cần cho đánh giá validation; không chứa checkpoint YOLO11n, thông tin đăng nhập hoặc môi trường Python Windows.

Ba kiểm thử Colab đã qua; đã dựng model v8n trên CPU với 1.000 đầu ra, kiểm tra backbone giữ trọng số và 36 hàng classification remap theo tên. Không chạy training local khi kiểm tra. Notebook mặc định tắt train, đọc ảnh tại `/content`, sao lưu checkpoint/CSV vào Drive sau mỗi epoch và có chế độ resume từ Drive. Đã kiểm tra mã Python trong các cell. Chưa upload hoặc chạy trên GPU Colab: cần tài khoản Google, mount Drive và GPU được cấp. Bộ dữ liệu và model backend vẫn nguyên; lịch tự động cũ đã xóa.

Cập nhật sau yêu cầu đưa lên Colab: **đã upload đủ 3 file** vào [Drive](https://drive.google.com/drive/folders/1ltcwEKFwA3aZSxuqtkQ7Ch24FPu9fwjv), gồm ZIP 4,35 GiB, JSON và notebook; UI xác nhận “Đã tải 3 mục lên”. Đã mở [notebook trên Colab](https://colab.research.google.com/drive/16_OMHu1FAaLFgrc_ZZ_G3fgPSp9teN7z) và xác nhận đúng nội dung YOLOv8n 1.000 nhãn. Chưa kết nối runtime, mount Drive hoặc chạy cell/training trên Colab.

Cập nhật sau yêu cầu bắt đầu train: đã kết nối Tesla T4; người dùng tự hoàn tất cấp quyền Drive. Đã xác nhận mount, thư viện CUDA và đủ các split, bật `RUN_TRAINING=True` rồi chạy cell train cho `v8n-1000-colab-001` (50 epoch tối đa, 640, batch 4, workers 2). Kiểm tra cuối: cell thực thi hơn 4 phút, GPU dùng 1,7/15 GiB, không thấy lỗi khởi động; chưa đọc được kết quả epoch đầu. Theo yêu cầu mới, để Colab tự chạy và không theo dõi liên tục, không tạo automation. Backend và training local vẫn giữ nguyên trạng thái dừng; checkpoint được sao lưu theo callback trong runner Colab.

Kiểm tra theo yêu cầu lúc khoảng 16:51 ngày 04/11 (UTC+7): **đã hoàn thành 8 epoch**, Colab vẫn hiển thị cell đang chạy và GPU được dùng. Đã tải bản `results.csv` thực từ Drive về `reports/results-colab-20261104-1648.csv`: có đủ hàng epoch 1–8, tổng thời gian 5.759,98 giây (~12 phút/epoch). Drive preview chỉ hiện hàng đầu cũ nên không dùng preview để kết luận số epoch. Epoch 8: precision 0,28518; recall 0,24616; mAP50 0,16943; mAP50–95 0,10833. Epoch 1 tương ứng mAP50 0,03341 và mAP50–95 0,01919. Đây là proxy validation, chưa chấm chính thức với baseline. `best.pt` và `last.pt` đều có trên Drive, khoảng 32,6 MiB, cập nhật 16:47. Không can thiệp hoặc khởi động lại training; không tạo lịch theo dõi.

Kiểm tra tiếp theo theo yêu cầu lúc khoảng 19:06 ngày 04/11 (UTC+7): **đã hoàn thành 19/50 epoch**. Bản CSV thực lưu tại `reports/results-colab-20261104-1904.csv`, gồm đủ hàng 1–19, tổng thời gian 13.640,4 giây (~12 phút/epoch). Epoch 19: precision 0,40204; recall 0,27451; mAP50 0,23688; mAP50–95 0,15817. Đã xác nhận `best.pt` và `last.pt` trên Drive đều cập nhật lúc 18:58; Colab vẫn kết nối T4, GPU dùng 1,9/15 GiB, chưa thấy lỗi. Colab hiển thị thời lượng còn khoảng 1 giờ (ước tính, không bảo đảm), có thể cần resume từ checkpoint ở phiên sau để đạt 50 epoch. Không đổi cấu hình, không dừng hoặc khởi động lại job và không tạo automation.

Kiểm tra theo yêu cầu khoảng 20:40 ngày 04/11 (UTC+7): **Colab đã ngắt phiên GPU và hiện từ chối cấp GPU do hạn mức sử dụng**. Không chuyển sang CPU, không mua tài nguyên và không chạy lại local. Đã tải CSV mới về `reports/results-colab-20261104-2040.csv`: có đủ 25 epoch, tổng thời gian 17.944,2 giây (~4 giờ 59 phút). Epoch 25: precision 0,38066; recall 0,30091; mAP50 0,25480; mAP50–95 0,17036. `best.pt` và `last.pt` đều vẫn có trên Drive, mỗi file khoảng 32,6 MiB, cập nhật lúc 20:10. Chưa tải/nạp checkpoint lần này để kiểm tra optimizer; đây vẫn là checkpoint chưa hoàn tất lịch train, dự kiến resume bằng `MODE='resume-drive'` và cùng tên run khi GPU được cấp lại. Chưa đủ 50 epoch, chưa chạy đánh giá LVIS chính thức hoặc thay model backend. Không tạo theo dõi định kỳ theo yêu cầu người dùng.

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

## Job bộ lớn — đã dừng sau epoch đầu

Tên: `candidate-1000-20261104`.

**Yêu cầu mới của người dùng: dừng sau epoch đầu và báo kết quả. Không tự resume hoặc train thêm.** Đã chạy `stop_after_epoch.py --name candidate-1000-20261104 --epoch 1` để chờ validation và checkpoint `epoch0.pt` hoàn chỉnh rồi dừng cây tiến trình job. Checkpoint và `results.csv` được giữ lại; runner bị dừng có chủ đích để không tiếp tục lịch cũ. Trạng thái bộ dừng nằm ở `runs/job-candidate-1000-20261104/stop-after-epoch.json`. Lịch theo dõi đã cập nhật theo yêu cầu mới, không cho phép tự train lại; xóa sau khi dừng và báo kết quả.

**Kết quả lúc 13:45 ngày 04/11/2026 (UTC+7):** đã dừng lúc 13:44:24 sau đúng một epoch hoàn chỉnh, gồm training 21.507 ảnh và validation 3.296 ảnh. `results.csv` chỉ có một hàng epoch 1; log chưa bắt đầu epoch 2. Không còn tiến trình runner/trainer khi kiểm tra ngoài sandbox; GPU trở về 0 MiB. Lịch theo dõi đã được xóa, không tự chạy thêm.

| Chỉ số validation trong train (proxy) | Epoch 1 |
|---|---:|
| Precision | 0,08388 |
| Recall | 0,10671 |
| mAP50 | 0,04696 |
| mAP50–95 | 0,02717 |

Train loss: box 1,81681; classification 3,36681; DFL 1,60524. Phần train khoảng 37 phút 17 giây; validation khoảng 24 phút 52 giây. Chỉ số còn thấp; đây là proxy của trainer, chưa phải báo cáo evaluator LVIS chính thức và không được so trực tiếp với tổng AP của model cũ. Không chấm test hoặc chạy assess sau yêu cầu dừng này.

Đã nạp `weights/epoch0.pt` trên CPU, xác nhận epoch lưu nội bộ bằng 0 (tức epoch đầu), đủ 1.000 tên lớp và còn optimizer để có thể tiếp tục nếu người dùng yêu cầu sau này. `best.pt`, `last.pt`, `epoch0.pt` có SHA-256 giống nhau. Checksum model backend vẫn nguyên. Báo cáo lưu tại `reports/candidate-1000-20261104-epoch1.json`.

Các mốc bên dưới là lịch sử chạy, không phải yêu cầu tiếp tục training:

- Manifest đã chọn 21.507 ảnh train / 3.296 validation / 1.390 test; có 415.840 bounding box trong train.
- Job nền tải và kiểm tra toàn bộ ảnh được chọn, sau đó fine-tune tối đa 100 epoch, có early stopping và checkpoint để resume.
- Cập nhật 12:33 ngày 04/11/2026 (UTC+7): đã tải và kiểm tra đủ 26.193 ảnh, không có lỗi/ảnh trùng giữa các split trong audit. Hash READY khớp provenance. Bộ lớn đã bắt đầu train lúc 12:27 trên RTX 3060, ảnh 640, batch 4, workers 2; epoch đầu đang chạy, chưa có kết quả validation của bộ lớn để kết luận chất lượng.
- Kiểm tra lúc 12:40: log dừng lúc 12:35:37 ở batch 951/5.377 của epoch đầu; không còn tiến trình cha/con khi kiểm tra ngoài sandbox, không có traceback hoặc checkpoint. Chưa xác định nguyên nhân ngắt. Đã giữ lại thư mục run trong `runs/candidate-1000-20261104-interrupted-1235/` và trạng thái cũ trong thư mục job. Khởi động lại lúc 12:41 từ bộ dữ liệu đã xác minh, không tải lại ảnh; do chưa có checkpoint nên phải chạy lại epoch đầu.
- Xác nhận lúc 12:43: lần chạy mới đã đến batch 74/5.377 của epoch 1, khoảng 2,4 batch/giây; GPU hoạt động 96%, dùng khoảng 1,8 GiB VRAM. Log tiếp tục tăng, loss hữu hạn; chưa có kết quả validation của epoch hoàn chỉnh.
- Cập nhật lúc 12:55: training vẫn chạy bình thường, batch 1.944/5.377 (36% epoch 1/100), khoảng 2,4–2,5 batch/giây. GPU 93%, VRAM khoảng 2 GiB, nhiệt độ 74°C; chưa hoàn tất epoch đầu và chưa có kết quả validation mới.
- Điều kiện kỹ thuật trước khi train: job pilot phải hoàn thành huấn luyện và đánh giá. Điều kiện này đã đạt.
- Kết quả cuối được xuất sang `reports/candidate-1000-20261104-val/`; không tự triển khai vào backend.
- Đã thêm `assess.py` để chấm baseline cũ trên cùng bộ validation lớn và so sánh các lớp tương đương. Job khởi động lại lúc 12:41 dùng runner hiện tại, có bước assess sau evaluate; vẫn cần kiểm tra báo cáo assessment thực sự hoàn tất.
- Người dùng đã đồng ý rõ bật theo dõi tự động mỗi 15 phút để kiểm tra job, sửa lỗi/tiếp tục training và đánh giá. Đã tạo heartbeat ACTIVE trong chat này: `theo-d-i-training-model-1-000-nh-n`, tên “Theo dõi training model 1.000 nhãn”. Theo dõi giữ im lặng khi không có thay đổi đáng kể và chạy assess sau khi job hiện hành hoàn tất. Không tạo lịch trùng.
- Xem trạng thái thực tế trong `runs/job-candidate-1000-20261104/status.json` và tiến độ tải trong `prepare.log` cùng thư mục, hoặc chạy `python training/status.py`.

## Dữ liệu cần bổ sung

Tám khái niệm cũ chưa có liên kết dữ liệu LVIS đủ rõ: earbuds, charging case, headphones, tablet, phone, game controller, board, pomegranate. Không gộp nhầm tai nghe chụp tai với mọi loại earphone hoặc board với mọi loại bảng.

Một số lớp LVIS hiếm thiếu mẫu train và thiếu ground truth val/test. Cụ thể profile lớn có 118 lớp chưa có mẫu validation, 274 lớp chưa có mẫu test. Báo cáo sẽ đánh dấu thiếu bằng chứng; chưa thể tuyên bố nhận diện tốt cả 1.000 lớp. Cần bổ sung dữ liệu và ảnh điện thoại độc lập trước khi nghiệm thu.

Model cũ và mã backend/frontend đang dùng được giữ nguyên. Các thay đổi trò chơi đã có sẵn trước phiên training không thuộc công việc này.
