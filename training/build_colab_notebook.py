"""Generate the portable Colab notebook; does not execute its cells."""
import json
from pathlib import Path
from textwrap import dedent

cells = []


def cell(kind, text):
    entry = dict(cell_type=kind, metadata={}, source=dedent(text).strip().splitlines(True))
    if kind == 'code':
        entry.update(execution_count=None, outputs=[])
    cells.append(entry)


cell('markdown', '''
# Train YOLOv8n — 1.000 nhãn trên Google Colab

Dùng lại 26.193 ảnh: 21.507 train, 3.296 validation, 1.390 test giữ riêng.
Tạo run mới từ model YOLOv8n 51 nhãn cũ; không dùng checkpoint YOLO11n.
Danh mục 1.000 nhãn còn cần rà soát, có lớp thiếu mẫu. Không cam kết chất lượng trước đánh giá.

1. Upload `colab-training-v8n.zip` và `colab-training-v8n.json` vào thư mục
   **My Drive/ai-image-english-learning/** của tài khoản Google của bạn.
2. Chọn **Runtime → Change runtime type → GPU** và kết nối hosted runtime của Google.
3. Chạy các cell theo thứ tự. Cell train mặc định tắt; đọc cấu hình trước khi bật.

Ảnh được giải nén vào `/content`, checkpoint/CSV được sao lưu vào Drive sau mỗi epoch.
Colab có giới hạn phiên và GPU thay đổi tùy khả dụng. Phiên mất trước checkpoint đầu
thì phải chạy lại epoch đầu; không dùng thủ thuật giữ phiên hoặc vượt giới hạn.
''')
cell('code', '''
from pathlib import Path
assert Path('/content').is_dir(), 'Notebook này dành cho hosted runtime Google Colab.'
from google.colab import drive
drive.mount('/content/drive')
DRIVE_ROOT = Path('/content/drive/MyDrive/ai-image-english-learning')
ARCHIVE = DRIVE_ROOT / 'colab-training-v8n.zip'
METADATA = DRIVE_ROOT / 'colab-training-v8n.json'
assert ARCHIVE.is_file() and METADATA.is_file(), 'Upload ZIP và JSON trước.'
''')
cell('code', '''
# Giữ PyTorch CUDA có sẵn trên Colab; không dùng lock file Windows.
import subprocess, sys
subprocess.run([sys.executable, '-m', 'pip', 'install',
                'ultralytics==8.4.188', 'lvis==0.5.3', 'pycocotools>=2.0.11',
                'numpy<2.4', 'Pillow>=11.3'], check=True)
import torch
assert torch.cuda.is_available(), 'Chọn GPU runtime trước; không chạy train bằng CPU.'
print('PyTorch:', torch.__version__, 'CUDA:', torch.version.cuda)
print('GPU:', torch.cuda.get_device_name(0))
''')
cell('code', '''
import hashlib, json, shutil, zipfile
LOCAL_ARCHIVE = Path('/content/colab-training.zip')
WORKSPACE = Path('/content/ai-image-english-learning')
info = json.loads(METADATA.read_text())
if not LOCAL_ARCHIVE.exists():
    shutil.copyfile(ARCHIVE, LOCAL_ARCHIVE)
hasher = hashlib.sha256()
with LOCAL_ARCHIVE.open('rb') as stream:
    for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
        hasher.update(chunk)
digest = hasher.hexdigest()
assert digest == info['sha256'], 'Archive hash không đúng; tải/copy lại gói ZIP.'
WORKSPACE.mkdir(exist_ok=True)
with zipfile.ZipFile(LOCAL_ARCHIVE) as archive:
    for entry in archive.infolist():
        target = (WORKSPACE / entry.filename).resolve()
        assert target.is_relative_to(WORKSPACE.resolve()), 'Unsafe archive path'
    archive.extractall(WORKSPACE)
sys.path.insert(0, str(WORKSPACE / 'training'))
from colab_run import relocate_dataset
manifest = relocate_dataset(WORKSPACE / 'training/data/prepared/full')
assert hashlib.sha256((WORKSPACE / 'training/data/prepared/full/manifest.json').read_bytes()).hexdigest() == info['manifest_sha256']
print('Đã kiểm tra:', len(manifest['classes']), 'lớp; số ảnh từng split:',
      {name: len(records) for name, records in manifest['splits'].items()})
''')
cell('markdown', '''
## Cấu hình train

Lần đầu dùng `MODE = "v8-new"`, đặt tên run riêng. Muốn tiếp tục một phiên Colab bị ngắt,
đặt `MODE = "resume-drive"`, giữ tên run và bộ dữ liệu, chọn tổng số epoch lớn hơn số đã học.
`EPOCHS` là tổng tối đa; early stopping có thể dừng sớm. Batch 4 là điểm bắt đầu thận trọng,
chưa benchmark tốc độ/VRAM trên GPU Colab được cấp. Kiểm tra epoch đầu trước khi tăng batch.
Muốn chỉ chạy thử một epoch thì đặt `EPOCHS = 1`.

Validation trong train là proxy có xử lý nhãn LVIS chưa xác minh. Không dùng YOLO.train
thông thường thay thế custom trainer. Chưa dùng test để chọn model.
''')
cell('code', '''
MODE = 'v8-new'  # 'v8-new' hoặc 'resume-drive'
RUN_NAME = 'v8n-1000-colab-001'
EPOCHS = 50
BATCH = 4
WORKERS = 2
RUN_TRAINING = False  # Đổi True khi bạn muốn bắt đầu trên GPU Colab.
if RUN_TRAINING:
    command = [sys.executable, '-u', str(WORKSPACE / 'training/colab_run.py'),
               '--mode', MODE, '--name', RUN_NAME, '--drive-root', str(DRIVE_ROOT),
               '--epochs', str(EPOCHS), '--batch', str(BATCH), '--workers', str(WORKERS)]
    subprocess.run(command, cwd=WORKSPACE, check=True)
else:
    print('Chưa train. Kiểm tra cấu hình rồi đổi RUN_TRAINING = True.')
''')
cell('code', '''
import pandas as pd
results = DRIVE_ROOT / 'runs' / RUN_NAME / 'results.csv'
if results.exists():
    display(pd.read_csv(results).tail(10))
    print('Checkpoint:', results.parent / 'weights')
else:
    print('Chưa có epoch hoàn chỉnh và checkpoint trong Drive.')
''')
cell('markdown', '''
## Sau khi chốt ứng viên: đánh giá trên cùng validation

Cell này mặc định tắt; không train thêm. Chấm candidate và baseline cũ bằng evaluator LVIS
trên cùng 3.296 ảnh, cùng lớp tương đương; có thể mất nhiều thời gian và RAM.
Không so tổng AP 51 lớp và 1.000 lớp như cùng bài toán. Báo cáo cũng ghi nhãn thiếu ground truth.
''')
cell('code', '''
RUN_ASSESSMENT = False
if RUN_ASSESSMENT:
    local_run = WORKSPACE / 'training/runs' / RUN_NAME
    local_run.mkdir(parents=True, exist_ok=True)
    shutil.copytree(DRIVE_ROOT / 'runs' / RUN_NAME / 'weights', local_run / 'weights', dirs_exist_ok=True)
    try:
        subprocess.run([sys.executable, '-u', str(WORKSPACE / 'training/assess.py'),
                        '--name', RUN_NAME, '--profile', 'full'], cwd=WORKSPACE, check=True)
    finally:
        reports = WORKSPACE / 'training/reports'
        if reports.exists():
            shutil.copytree(reports, DRIVE_ROOT / 'reports', dirs_exist_ok=True)
else:
    print('Chưa chạy đánh giá cuối.')
''')

notebook = dict(cells=cells, metadata=dict(kernelspec=dict(display_name='Python 3',
                language='python', name='python3'), language_info=dict(name='python'),
                accelerator='GPU', colab=dict(provenance=[])), nbformat=4, nbformat_minor=5)
# Stable cell ids for notebook format 4.5.
for index, entry in enumerate(cells):
    entry['id'] = f'colab-{index:02d}'
output = Path(__file__).with_name('train_yolov8n_colab.ipynb')
output.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding='utf-8')
print(output)
