# Huấn luyện YOLOv8n trên Google Colab

Người dùng đã chọn tạo run YOLOv8n mới từ model cũ, dùng lại bộ 26.193 ảnh. Không dùng checkpoint YOLO11n. Training trên máy và lịch tự động hiện đã dừng.

## Đã đưa lên Drive và Colab

Ngày 04/11/2026: đã tải đủ notebook, ZIP 4,35 GiB (4.673.033.743 byte) và JSON vào thư mục dự án. Google Drive hiển thị **Đã tải 3 mục lên**; notebook đã mở thành công trên Colab.

Sau yêu cầu bắt đầu train: người dùng đã tự cấp quyền Drive; Colab hiển thị `Mounted at /content/drive`. Môi trường thực tế PyTorch 2.11.0+cu130, CUDA 13.0, Tesla T4. Cell chuẩn bị xác nhận đủ 1.000 lớp và 21.507 train / 3.296 val / 1.390 test. Đã đổi `RUN_TRAINING=True` trong notebook trên Colab và chạy cell train, run `v8n-1000-colab-001`, tối đa 50 epoch, 640, batch 4, workers 2. Lần kiểm tra cuối cell đang thực thi hơn 4 phút, GPU dùng 1,7/15 GiB, chưa thấy traceback; chưa có chỉ số epoch hoàn chỉnh được đọc. Không suy diễn epoch hoặc chất lượng từ RAM GPU. Người dùng yêu cầu để chạy tự động, không cần theo dõi liên tục: không tạo lịch giám sát hay job local. Checkpoint/CSV được runner sao lưu vào Drive sau mỗi lần lưu model.

- [Mở notebook trên Colab](https://colab.research.google.com/drive/16_OMHu1FAaLFgrc_ZZ_G3fgPSp9teN7z)
- [Thư mục dữ liệu trên Drive](https://drive.google.com/drive/folders/1ltcwEKFwA3aZSxuqtkQ7Ch24FPu9fwjv)

## File đã chuẩn bị

- `train_yolov8n_colab.ipynb`: mở bằng Google Colab.
- `exports/colab-training-v8n.zip`: gói ảnh, nhãn, manifest, mã trainer và model v8n cũ; không chứa `.env`, API key hoặc môi trường Python Windows.
- `exports/colab-training-v8n.json`: SHA-256, kích thước và số ảnh để notebook kiểm tra trước khi giải nén.

Gói còn có annotation LVIS validation và ánh xạ nhãn cũ để đánh giá hai model trên cùng tập ảnh sau này. Test giữ riêng. Không tự triển khai model vào backend.

## Chạy

1. Upload ZIP và JSON vào **My Drive/ai-image-english-learning/**. Cần đủ chỗ cho gói dữ liệu và các checkpoint. Không giải nén hàng chục nghìn ảnh trực tiếp trong Drive.
2. Vào <https://colab.research.google.com/>, chọn **File → Upload notebook**, mở notebook đã chuẩn bị.
3. Chọn **Runtime → Change runtime type → GPU**, dùng hosted runtime của Google, không kết nối local runtime.
4. Chạy các cell mount Drive, cài thư viện và kiểm tra/giải nén dữ liệu. Ảnh được đọc từ `/content`.
5. Cell cấu hình mặc định `MODE='v8-new'`, `EPOCHS=50`, `BATCH=4`, `RUN_TRAINING=False`. Chọn số epoch rồi đổi `RUN_TRAINING=True` khi muốn bắt đầu. Đặt `EPOCHS=1` nếu muốn kiểm tra một epoch trước. Không có training nào được chạy chỉ từ việc tạo các file này.
6. Xem checkpoint và CSV tại **My Drive/ai-image-english-learning/runs/v8n-1000-colab-001/**. Callback sao lưu sau mỗi epoch đã lưu xong.

Nếu Colab ngắt phiên: mở lại notebook, chọn GPU, chạy lại các cell chuẩn bị, giữ tên run và chuyển `MODE='resume-drive'`. Cần checkpoint `last.pt` còn optimizer; `EPOCHS` là tổng số epoch muốn đạt, phải lớn hơn số đã học. Phiên ngắt trước checkpoint đầu sẽ phải chạy lại epoch đầu. Run đã hoàn tất và strip optimizer không được coi là checkpoint để resume; giữ best để đánh giá.

## Đã kiểm tra và giới hạn

- Ba kiểm thử cho chuyển đường dẫn, giữ nguyên manifest, kiểm tra file ảnh/nhãn, sao lưu checkpoint hoàn chỉnh và notebook mặc định không tự train.
- Đã dựng model trên CPU từ đúng v8n cũ với đầu ra 1.000 lớp; backbone giữ trọng số, 36 hàng classification được remap theo tên khớp. Không chạy training khi kiểm tra này.
- Notebook và runner dùng `ultralytics==8.4.188`, giữ PyTorch CUDA có sẵn trên Colab. Không cài lock file Windows.
- Chưa chạy notebook trên GPU Colab thực tế: cần tài khoản Google, mount Drive và GPU được cấp. Batch 4 chưa được benchmark trên Colab; không bảo đảm nhanh hơn laptop ở mọi GPU.
- Dữ liệu LVIS có nhãn chưa xác minh: phải dùng `VerifiedTrainer` đã kèm theo, không thay bằng trainer mặc định. Đánh giá trong train là proxy; đánh giá cuối có cell riêng mặc định tắt, so cùng validation và lớp tương đương với baseline cũ.
- GPU và thời lượng phiên miễn phí không được bảo đảm. Không bật trả phí hoặc dùng thủ thuật né giới hạn.

Nguồn chính thức: [Colab FAQ](https://research.google.com/colaboratory/faq.html), [Ultralytics training](https://docs.ultralytics.com/modes/train/).
