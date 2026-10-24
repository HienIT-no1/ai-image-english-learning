import io
import urllib.parse
from pathlib import Path
import cv2
import numpy as np
from PIL import Image as PILImage, ImageOps
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from ultralytics import YOLO

from app.models.image import Image
from app.models.user import User
from app.models.vocabulary import Vocabulary
from app.schemas.ai import BoundingBox, DetectionItem, VocabularyDetail
from app.services.cloudinary_service import upload_image_bytes

# Load YOLO model once (support execution from any working directory)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
WEIGHTS_PATH = BASE_DIR / "weights" / "best.pt"
if not WEIGHTS_PATH.exists():
    WEIGHTS_PATH = Path("weights/best.pt")
model = YOLO(str(WEIGHTS_PATH))


def get_default_audio_url(word: str) -> str:
    """Generate free US pronunciation link if DB does not have one."""
    encoded = urllib.parse.quote_plus(word)
    return f"https://dict.youdao.com/dictvoice?audio={encoded}&type=2"


def lookup_vocabulary(db: Session, raw_label: str) -> VocabularyDetail:
    """
    Search vocabulary in database to retrieve phonetic (IPA), audio, and Vietnamese meanings.
    """
    normalized_label = raw_label.replace("_", " ").strip()
    word_search = db.query(Vocabulary).filter(
        or_(
            func.lower(Vocabulary.word) == raw_label.lower(),
            func.lower(Vocabulary.word) == normalized_label.lower()
        )
    ).first()

    if word_search:
        meaning_vi = None
        if word_search.meanings and len(word_search.meanings) > 0:
            meaning_vi = word_search.meanings[0].meaning_vi

        audio_url = word_search.audio_url or get_default_audio_url(word_search.word)

        return VocabularyDetail(
            vocabulary_id=word_search.vocabulary_id,
            word=word_search.word,
            ipa=word_search.ipa,
            part_of_speech=word_search.part_of_speech or "noun",
            meaning_vi=meaning_vi,
            audio_url=audio_url,
        )

    # Fallback if the word is not yet in the vocabulary database
    return VocabularyDetail(
        vocabulary_id=None,
        word=normalized_label,
        ipa=None,
        part_of_speech="noun",
        meaning_vi=None,
        audio_url=get_default_audio_url(normalized_label),
    )


def detect_objects_from_bytes(image_bytes: bytes, db: Session, conf: float = 0.35):
    """
    Run YOLO inference on image bytes and enrich with vocabulary info.
    Auto-corrects EXIF rotation for smartphone camera photos.
    """
    img = None
    try:
        pil_img = PILImage.open(io.BytesIO(image_bytes))
        pil_img = ImageOps.exif_transpose(pil_img)
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    except Exception:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Invalid image file format")

    height, width, _ = img.shape
    results = model.predict(source=img, conf=conf, verbose=False)

    detections: list[DetectionItem] = []

    for r in results:
        if not r.boxes:
            continue
        for box in r.boxes:
            cls_id = int(box.cls[0])
            raw_label = model.names.get(cls_id, f"object_{cls_id}")
            confidence = round(float(box.conf[0]), 3)

            xyxy = box.xyxy[0].tolist()
            box_coords = BoundingBox(
                x1=round(xyxy[0], 2),
                y1=round(xyxy[1], 2),
                x2=round(xyxy[2], 2),
                y2=round(xyxy[3], 2),
            )

            vocab_detail = lookup_vocabulary(db, raw_label)

            detections.append(
                DetectionItem(
                    label=raw_label,
                    confidence=confidence,
                    box=box_coords,
                    vocabulary=vocab_detail,
                )
            )

    return detections, width, height


def capture_and_save(
    image_bytes: bytes,
    user_id: int | None,
    db: Session,
    conf: float = 0.35
):
    """
    1. Detect objects using AI
    2. Upload image to Cloudinary (folder: app_img_eng)
    3. Save image URL to PostgreSQL
    4. Return full response
    """
    # Step 1: Detect objects
    detections, width, height = detect_objects_from_bytes(image_bytes, db, conf=conf)

    # Step 2: Upload to Cloudinary
    secure_url = upload_image_bytes(image_bytes, folder="app_img_eng")

    # Step 3: Determine user_id to associate with Image
    final_user_id = user_id
    if final_user_id is None:
        # Fallback to the first available user in DB for demo/testing
        first_user = db.query(User.user_id).first()
        if first_user:
            final_user_id = first_user[0]

    # Step 4: Save record to PostgreSQL
    image_record = None
    if final_user_id is not None:
        image_record = Image(
            user_id=final_user_id,
            image_url=secure_url,
            source_type="CAMERA",
        )
        db.add(image_record)
        db.commit()
        db.refresh(image_record)

    return {
        "image_id": image_record.image_id if image_record else None,
        "image_url": secure_url,
        "image_width": width,
        "image_height": height,
        "count": len(detections),
        "detections": detections,
    }
