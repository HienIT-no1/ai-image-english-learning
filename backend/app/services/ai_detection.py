"""Validate images and compare independent YOLO predictions without DB writes."""
import io
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Lock
import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from ultralytics import YOLO
from app.core.config import settings

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parents[2]
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
_predict_lock = Lock()

class InvalidImageError(ValueError):
    pass

class DetectionUnavailableError(RuntimeError):
    pass

@dataclass(frozen=True)
class Candidate:
    label: str
    confidence: float
    box: tuple[float, float, float, float]

def decode_image(data: bytes) -> np.ndarray:
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise InvalidImageError("Ảnh đang trống hoặc vượt quá giới hạn 10 MB.")
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise InvalidImageError("Ảnh quá lớn. Hãy chọn ảnh dưới 25 megapixel.")
            image = ImageOps.exif_transpose(image).convert("RGB")
            return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    except InvalidImageError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise InvalidImageError("Không đọc được ảnh. Hãy chọn một file ảnh hợp lệ.") from exc

@lru_cache(maxsize=2)
def _load_model(filename):
    path = BASE_DIR / "weights" / filename
    if not path.is_file():
        logger.error("Missing AI weights %s; run python setup_ai_models.py", path)
        raise DetectionUnavailableError("Dịch vụ nhận diện chưa sẵn sàng. Vui lòng thử lại sau.")
    return YOLO(str(path))

def _candidates(model, image, conf):
    return [Candidate(str(model.names[int(b.cls[0])]), float(b.conf[0]), tuple(float(v) for v in b.xyxy[0].tolist()))
            for result in model.predict(source=image, conf=conf, verbose=False) for b in result.boxes]

def overlap(a, b):
    x1,y1=max(a.box[0],b.box[0]),max(a.box[1],b.box[1])
    x2,y2=min(a.box[2],b.box[2]),min(a.box[3],b.box[3])
    intersection=max(0.0,x2-x1)*max(0.0,y2-y1)
    aa=max(0.0,a.box[2]-a.box[0])*max(0.0,a.box[3]-a.box[1])
    ab=max(0.0,b.box[2]-b.box[0])*max(0.0,b.box[3]-b.box[1])
    return intersection/(aa+ab-intersection) if aa+ab-intersection else 0.0

# Only equivalent vocabulary classes; e.g. generic COCO bottle is not assumed to be a water bottle.
REFERENCE_LABELS = {
    "cell phone":"Phone", "tv":"tv", "mouse":"Mouse", "keyboard":"Keyboard", "laptop":"laptop",
    "apple":"apple", "banana":"banana", "orange":"orange", "backpack":"backpack", "bed":"bed",
    "chair":"chair", "clock":"clock", "couch":"couch", "dining table":"dining table",
    "microwave":"microwave", "oven":"oven", "refrigerator":"refrigerator", "scissors":"scissors",
    "sink":"sink", "toaster":"toaster", "toilet":"toilet",
}

def reconcile(custom, reference):
    """Same object only: IoU >= .5, reference >= .75 and >= custom + .15.

    Scores from different models are not calibrated probabilities; this conservative
    policy still needs validation on labelled photos. There are no photo-specific rules.
    """
    result=[]
    for original in custom:
        matches=[r for r in reference if r.label in REFERENCE_LABELS and r.confidence>=.75
                 and r.confidence>=original.confidence+.15 and overlap(original,r)>=.5]
        best=max(matches,key=lambda r:r.confidence,default=None)
        candidate=Candidate(REFERENCE_LABELS[best.label],best.confidence,best.box) if best else original
        if not any(candidate.label.lower()==old.label.lower() and overlap(candidate,old)>=.65 for old in result):
            result.append(candidate)
    return result

def detect_candidates(image, conf):
    if float(image.reshape(-1,3).std(axis=0).max())<6.0:
        return []
    try:
        # Ultralytics predictors retain mutable state between requests.
        with _predict_lock:
            custom=_candidates(_load_model("best.pt"),image,conf)
            if not custom or not settings.AI_REFERENCE_ENABLED:
                return custom
            reference=_candidates(_load_model("yolo11n.pt"),image,max(conf,.75))
        return reconcile(custom,reference)
    except DetectionUnavailableError:
        raise
    except Exception as exc:
        logger.exception("YOLO inference failed")
        raise DetectionUnavailableError("Không thể nhận diện lúc này. Vui lòng thử lại sau.") from exc
