# Training model nhận diện 1.000 lớp

Công cụ độc lập với backend. Dữ liệu, môi trường Python và kết quả được lưu trong `training/`; không tự ghi đè `backend/weights/best.pt` hoặc thay đổi database.

Tiến độ triển khai và kết quả pilot: [PROGRESS.md](PROGRESS.md). Danh mục dễ đọc: [catalog-review.md](catalog-review.md).

Người dùng đã chọn chuyển sang **YOLOv8n trên Google Colab**, tạo run mới từ model v8n cũ. Hướng dẫn và notebook: [COLAB.md](COLAB.md), [train_yolov8n_colab.ipynb](train_yolov8n_colab.ipynb). Các lệnh Windows bên dưới là quy trình cũ; không tự khởi động lại training local.

## Lựa chọn dữ liệu

`catalog.json` chứa 1.000 lớp có dữ liệu LVIS thật, định nghĩa và mã category nguồn. Danh mục ưu tiên các lớp phổ biến và 41 khái niệm cũ có liên kết nghĩa rõ ràng. Đây là danh mục khởi đầu: một số mục còn cần rà soát độ phù hợp với từ vựng cơ bản. Nhãn trùng chữ hoa/chữ thường không được dùng để tăng số lượng.

Open Images chỉ được đối chiếu tên trong giai đoạn này. Mục `candidate_exact_name` chưa được phép đổi nhãn hoặc ghép ảnh tự động; chưa tải ảnh Open Images. Tám khái niệm cũ cần dữ liệu bổ sung hoặc kiểm tra nghĩa được ghi trong `legacy_coverage` và báo cáo coverage. Không coi các từ này là đã được bảo toàn trong model mới.

LVIS không gán nhãn đầy đủ cho mọi lớp trong mọi ảnh. `verified_training.py` chỉ tính classification loss cho lớp đã xác minh trên ảnh và các positive anchor có annotation; bỏ qua cặp ảnh/lớp chưa xác minh. Mosaic, MixUp, CutMix và Copy-Paste được tắt để tránh trộn các mask xác minh không đúng.

Bounding box được lấy trực tiếp từ annotation gốc, cắt theo biên ảnh và chuyển sang detection YOLO. Không trộn dòng segmentation vào file detection. Mỗi split giữ image ID riêng; khi tải ảnh còn kiểm tra SHA-256 để phát hiện ảnh trùng nội dung giữa các split.

Nguồn và provenance:

- LVIS: https://www.lvisdataset.org/ và https://docs.ultralytics.com/datasets/detect/lvis/
- Open Images: https://storage.googleapis.com/openimages/web/index.html
- Project Roboflow cũ, phiên bản 2: `xuanhien0123z-gmail-com/yolo_img_english`. Chưa tải lại; không lưu API key trong repo.
- `data/raw/provenance.json` lưu URL và SHA-256 của archive annotation thực sự tải được.
- Manifest ảnh lưu URL, image ID, license ID và nguồn nhãn; áp dụng điều khoản LVIS/COCO và giấy phép từng ảnh khi sử dụng/phân phối.

## Môi trường trên Windows

Chạy từ thư mục gốc dự án. Dùng môi trường mới, không cài CUDA PyTorch vào `.venv` backend đang dùng.

```powershell
py -3.14 -m venv training/.venv
.\training\.venv\Scripts\python.exe -m pip install torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cu128
.\training\.venv\Scripts\python.exe -m pip install -r training/requirements.txt
.\training\.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

Custom trainer được kiểm tra với Ultralytics 8.4.188. Nếu nâng thư viện, phải chạy lại kiểm thử gradient, một epoch thật và đọc lại checkpoint bằng loader chuẩn. Không im lặng chuyển sang CPU khi CUDA lỗi.

## Chuẩn bị và chạy thử

```powershell
.\training\.venv\Scripts\python.exe training/download.py --metadata
.\training\.venv\Scripts\python.exe training/prepare.py --profile pilot --images
.\training\.venv\Scripts\python.exe -m unittest discover -s training/tests -v
.\training\.venv\Scripts\python.exe training/train.py --profile pilot --name pilot-1000
.\training\.venv\Scripts\python.exe training/evaluate.py --model training/runs/pilot-1000/weights/best.pt --profile pilot --split val --imgsz 416 --name pilot-1000-val
```

Pilot chỉ chọn tối thiểu khoảng hai ảnh chứa mỗi lớp train nếu nguồn có đủ; một ảnh thường chứa nhiều lớp. Bộ này kiểm tra luồng và VRAM, không đủ để tuyên bố chất lượng nhận diện 1.000 từ. Không dùng pilot làm bản phát hành ứng dụng.

## Fine-tune với nhiều dữ liệu hơn

```powershell
.\training\.venv\Scripts\python.exe training/prepare.py --profile full --images
.\training\.venv\Scripts\python.exe training/train.py --profile full --epochs 100 --imgsz 640 --batch 4 --workers 2 --name candidate-1000
.\training\.venv\Scripts\python.exe training/evaluate.py --model training/runs/candidate-1000/weights/best.pt --profile full --split val --name candidate-1000-val
.\training\.venv\Scripts\python.exe training/assess.py --name candidate-1000 --profile full
```

Profile full chọn đến quota tối thiểu 100 ảnh chứa mỗi lớp train, 15 ảnh validation, 10 ảnh test theo thuật toán ưu tiên lớp ít mẫu. Đây không phải giới hạn cứng; ảnh được chọn cho lớp khác có thể làm số ảnh một lớp tăng. Các lớp nguồn có ít hơn quota phải được ghi nhận trong `coverage.json` và bổ sung sau. Không dùng ảnh validation/test làm train.

Tập val/test mới được tách cố định từ LVIS validation bằng hash image ID; tập train đến từ LVIS train. Điểm trên subset này không phải điểm benchmark LVIS đầy đủ. Tập test giữ riêng cho đánh giá cuối sau khi chốt mô hình và ngưỡng. Cần thêm một tập test ảnh điện thoại độc lập trước khi thay model của app.

Với RTX 3060 Laptop 6 GiB, pilot bắt đầu batch 2, ảnh 416, workers 0. Profile full mặc định batch 4, ảnh 640, workers 2; mức này cần được kiểm chứng bằng lần chạy thực tế. Nếu không vừa VRAM thì giảm batch/độ phân giải, không xóa dữ liệu hoặc tự thay mục tiêu nhãn. Thời gian chạy phụ thuộc dữ liệu, model, độ phân giải và nhiệt độ/thực trạng tài nguyên; phải đo qua pilot.

Để tiếp tục run bị ngắt:

```powershell
.\training\.venv\Scripts\python.exe training/train.py --profile full --name candidate-1000 --resume training/runs/candidate-1000/weights/last.pt
```

## Báo cáo và tiêu chí đưa vào ứng dụng

Job đã khởi động có thể theo dõi bằng `.\training\.venv\Scripts\python.exe training/status.py`. Nếu một job đã train xong nhưng bước đánh giá bị ngắt, dùng `run_job.py --profile <profile> --name <name> --from-stage evaluate` để chấm lại mà không train lại. Báo cáo hoàn chỉnh không bị ghi đè; báo cáo chưa hoàn chỉnh có thể tiếp tục cùng tên.

Trên máy này, `psutil.pid_exists` chạy trong sandbox có thể không thấy các tiến trình training chạy ngoài sandbox. Không suy ra job đã chết chỉ từ kết quả đó: kiểm tra timestamp log và xác minh PID/câu lệnh của job bằng kiểm tra chỉ đọc ngoài sandbox trước khi khởi động lại. Kết quả kiểm tra gần nhất được lưu tại `reports/monitor-state.json`.

- `data/prepared/<profile>/coverage.json`: số box của từng nhãn và danh sách từ cũ thiếu.
- `runs/<name>/provenance.json`: trọng số khởi tạo, phiên bản thư viện, tham số và hash manifest.
- `runs/<name>/status.json`: trạng thái kết thúc, lỗi hoặc checkpoint có thể resume.
- `reports/<name>/summary.json`, `per_class.json`: kết quả official LVIS bbox AP50/AP50-95, AR300, độ phủ và số mẫu từng lớp.
- Validation trong vòng train là proxy có lọc lớp chưa xác minh, dùng để chọn checkpoint. Báo cáo cuối dùng evaluator LVIS chính thức có xử lý category non-exhaustive.

Model cũ có thể được chấm trên cùng manifest bằng `evaluate.py --model backend/weights/best.pt ...`. Chỉ so sánh chất lượng các lớp cũ trên những lớp được ánh xạ nghĩa tương đương; không so sánh mAP tổng 51 lớp với tổng 1.000 lớp như cùng bài toán.

`assess.py` tự chấm baseline cũ trên cùng profile/split/độ phân giải, kiểm tra hash manifest giống nhau rồi tính chênh lệch AP trên các lớp cũ tương đương. Báo cáo còn đếm lớp mới đã có bằng chứng nhận diện và lớp chưa có ground truth. Các job full khởi động từ phiên bản runner mới có bước assess; job đã chạy trước khi thêm bước này sẽ được theo dõi và chạy assess riêng sau khi đánh giá xong.

Fine-tune tiếp từ ứng viên đã train bằng `train.py --profile full --name <tên-mới> --weights training/runs/<tên-cũ>/weights/best.pt`. Chỉ chạy lại khi đã xác định thay đổi dữ liệu/cấu hình phù hợp từ báo cáo; không lặp 100 epoch chỉ để kỳ vọng tự cải thiện.

Chưa có ngưỡng nghiệm thu chất lượng cuối. Trước khi thay backend, cần chứng minh cải thiện trên tập ảnh chung, kiểm tra suy giảm các từ cũ, hoàn thiện dữ liệu cho các từ thiếu, chuẩn bị nghĩa/IPA/ví dụ cho nhãn mới và đo độ trễ camera. Checkpoint thử nghiệm không tự được triển khai.
