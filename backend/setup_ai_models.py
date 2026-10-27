"""Download pinned official weights explicitly; no request-time model downloads."""
import hashlib
from pathlib import Path
import urllib.request
URL="https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt"
SHA256="0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1"
TARGET=Path(__file__).resolve().parent/"weights"/"yolo11n.pt"
def main():
    TARGET.parent.mkdir(exist_ok=True)
    if TARGET.is_file() and hashlib.sha256(TARGET.read_bytes()).hexdigest()==SHA256:
        print("YOLO11n reference weights verified.");return
    temp=TARGET.with_suffix(".download")
    try:
        urllib.request.urlretrieve(URL,temp)
        if hashlib.sha256(temp.read_bytes()).hexdigest()!=SHA256:
            raise RuntimeError("Reference model checksum mismatch; existing weights kept.")
        temp.replace(TARGET)
    finally:
        temp.unlink(missing_ok=True)
    print("Official YOLO11n reference weights installed and verified.")
if __name__=="__main__":main()
