import io
import urllib.parse
from datetime import datetime
from pathlib import Path
import cv2
import numpy as np
from PIL import Image as PILImage, ImageOps
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from ultralytics import YOLO

from app.models.image import Image
from app.models.topic import Topic, vocabulary_topics
from app.models.user import User
from app.models.vocabulary import Vocabulary, VocabularyMeaning
from app.schemas.ai import BoundingBox, DetectionItem, VocabularyDetail
from app.services.cloudinary_service import upload_image_bytes

# Load YOLO model once (support execution from any working directory)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
WEIGHTS_PATH = BASE_DIR / "weights" / "best.pt"
if not WEIGHTS_PATH.exists():
    WEIGHTS_PATH = Path("weights/best.pt")
model = YOLO(str(WEIGHTS_PATH))

# Accurate metadata dictionary for model classes (Word, IPA, Vietnamese meaning)
LABEL_METADATA: dict[str, tuple[str, str | None, str]] = {
    'airpods_buds': ('earbuds', '/ˈɪə.bʌdz/', 'tai nghe không dây'),
    'airpods_case': ('charging case', '/ˈtʃɑː.dʒɪŋ keɪs/', 'hộp sạc tai nghe'),
    'headphones': ('headphones', '/ˈhed.fəʊnz/', 'tai nghe chụp tai'),
    'ipad': ('tablet', '/ˈtæb.lət/', 'máy tính bảng'),
    'keyboard': ('keyboard', '/ˈkiː.bɔːd/', 'bàn phím máy tính'),
    'laptop': ('laptop', '/ˈlæp.tɒp/', 'máy tính xách tay'),
    'monitor': ('monitor', '/ˈmɒn.ɪ.tər/', 'màn hình máy tính'),
    'mouse': ('computer mouse', '/maʊs/', 'chuột máy tính'),
    'phone': ('phone', '/fəʊn/', 'điện thoại'),
    'playstation_controller': ('game controller', '/kənˈtrəʊ.lər/', 'tay cầm chơi game'),
    'xbox_controller': ('game controller', '/kənˈtrəʊ.lər/', 'tay cầm chơi game'),
    'apple': ('apple', '/ˈæp.əl/', 'quả táo'),
    'backpack': ('backpack', '/ˈbæk.pæk/', 'ba lô'),
    'banana': ('banana', '/bəˈnɑː.nə/', 'quả chuối'),
    'bed': ('bed', '/bed/', 'cái giường'),
    'board': ('board', '/bɔːd/', 'cái bảng'),
    'calculator': ('calculator', '/ˈkæl.kjə.leɪ.tər/', 'máy tính cầm tay'),
    'chair': ('chair', '/tʃeər/', 'cái ghế'),
    'cherry': ('cherry', '/ˈtʃer.i/', 'quả anh đào'),
    'clock': ('clock', '/klɒk/', 'đồng hồ'),
    'coconut': ('coconut', '/ˈkəʊ.kə.nʌt/', 'quả dừa'),
    'couch': ('sofa', '/ˈsəʊ.fə/', 'ghế sofa'),
    'cucumber': ('cucumber', '/ˈkjuː.kʌm.bər/', 'quả dưa chuột'),
    'dining table': ('dining table', '/ˈdaɪ.nɪŋ ˌteɪ.bəl/', 'bàn ăn'),
    'eraser': ('eraser', '/ɪˈreɪ.zər/', 'cục tẩy'),
    'grape': ('grape', '/ɡreɪp/', 'quả nho'),
    'kiwi': ('kiwi', '/ˈkiː.wiː/', 'quả kiwi'),
    'melon': ('melon', '/ˈmel.ən/', 'quả dưa lưới'),
    'microwave': ('microwave', '/ˈmaɪ.krə.weɪv/', 'lò vi sóng'),
    'notebook': ('notebook', '/ˈnəʊt.bʊk/', 'quyển vở ghi chép'),
    'orange': ('orange', '/ˈɒr.ɪndʒ/', 'quả cam'),
    'oven': ('oven', '/ˈʌv.ən/', 'lò nướng'),
    'peach': ('peach', '/piːtʃ/', 'quả đào'),
    'pear': ('pear', '/peər/', 'quả lê'),
    'pen': ('pen', '/pen/', 'bút mực'),
    'pencil': ('pencil', '/ˈpen.səl/', 'bút chì'),
    'pineapple': ('pineapple', '/ˈpaɪnˌæp.əl/', 'quả dứa'),
    'pomegranate': ('pomegranate', '/ˈpɒm.ɪˌɡræn.ɪt/', 'quả lựu'),
    'refrigerator': ('refrigerator', '/rɪˈfrɪdʒ.ər.eɪ.tər/', 'tủ lạnh'),
    'ruler': ('ruler', '/ˈruː.lər/', 'thước kẻ'),
    'scissors': ('scissors', '/ˈsɪz.əz/', 'cái kéo'),
    'sharpener': ('pencil sharpener', '/ˈʃɑː.pən.ər/', 'gọt bút chì'),
    'sink': ('sink', '/sɪŋk/', 'bồn rửa'),
    'strawberry': ('strawberry', '/ˈstrɔː.bər.i/', 'quả dâu tây'),
    'table': ('table', '/ˈteɪ.bəl/', 'cái bàn'),
    'toaster': ('toaster', '/ˈtəʊ.stər/', 'máy nướng bánh mì'),
    'toilet': ('toilet', '/ˈtɔɪ.lət/', 'bồn cầu'),
    'tv': ('television', '/ˈtel.ɪ.vɪʒ.ən/', 'ti vi'),
    'water_bottle': ('water bottle', '/ˈwɔː.tə ˌbɒt.əl/', 'bình nước'),
    'watermelon': ('watermelon', '/ˈwɔː.təˌmel.ən/', 'quả dưa hấu')
}


def get_default_audio_url(word: str) -> str:
    """Generate free US pronunciation link if DB does not have one."""
    encoded = urllib.parse.quote_plus(word)
    return f"https://dict.youdao.com/dictvoice?audio={encoded}&type=2"


def sync_model_labels_to_db(db: Session):
    """
    Startup sync: Automatically scans model classes from best.pt and ensures
    all words exist in PostgreSQL 'vocabularies' and 'vocabulary_meanings' tables.
    """
    topic = db.query(Topic).filter(Topic.slug == "objects").first()
    for _, raw_name in model.names.items():
        key = raw_name.lower().strip()
        word_str, ipa_str, meaning_str = LABEL_METADATA.get(
            key,
            (raw_name.replace("_", " ").strip(), None, raw_name.replace("_", " ").strip())
        )

        existing = db.query(Vocabulary).filter(func.lower(Vocabulary.word) == word_str.lower()).first()
        if not existing:
            new_vocab = Vocabulary(
                word=word_str,
                ipa=ipa_str,
                part_of_speech="noun",
                level="BEGINNER",
                audio_url=get_default_audio_url(word_str),
                created_at=datetime.utcnow()
            )
            db.add(new_vocab)
            db.flush()
            meaning = VocabularyMeaning(
                vocabulary_id=new_vocab.vocabulary_id,
                meaning_vi=meaning_str
            )
            db.add(meaning)
            if topic:
                db.execute(vocabulary_topics.insert().values(topic_id=topic.topic_id, vocabulary_id=new_vocab.vocabulary_id))
        else:
            # Fix mouse meaning to computer mouse in tech/object context
            if key == "mouse" and existing.meanings:
                existing.ipa = ipa_str or existing.ipa
                if not any("máy tính" in (m.meaning_vi or "") for m in existing.meanings):
                    existing.meanings[0].meaning_vi = "chuột máy tính"
    db.commit()


def lookup_vocabulary(db: Session, raw_label: str, auto_create: bool = False) -> VocabularyDetail:
    """
    Search vocabulary in database to retrieve phonetic (IPA), audio, and Vietnamese meanings.
    Supports plural/singular normalization (e.g. apples -> apple).
    auto_create: Only True when capturing photos to save newly confirmed words into DB.
    """
    key = raw_label.lower().strip()
    meta_word, meta_ipa, meta_meaning = LABEL_METADATA.get(
        key,
        (raw_label.replace("_", " ").strip(), None, raw_label.replace("_", " ").strip())
    )

    search_candidates = [raw_label, meta_word, raw_label.replace("_", " ").strip()]
    # Normalize plural s/es (e.g. apples -> apple, watches -> watch)
    norm = meta_word.lower()
    if norm.endswith("s") and len(norm) > 3 and norm not in ("scissors", "headphones", "glasses"):
        search_candidates.append(norm[:-1])
        if norm.endswith("es") and len(norm) > 4:
            search_candidates.append(norm[:-2])

    # Prioritize tailored meta_word first (e.g. computer mouse before animal mouse)
    word_search = db.query(Vocabulary).filter(func.lower(Vocabulary.word) == meta_word.lower()).first()
    if not word_search:
        for c in search_candidates:
            if c.lower() == meta_word.lower():
                continue
            word_search = db.query(Vocabulary).filter(func.lower(Vocabulary.word) == c.lower()).first()
            if word_search:
                break

    if word_search:
        meaning_vi = None
        if key in LABEL_METADATA and key == "mouse":
            meaning_vi = meta_meaning
        elif word_search.meanings and len(word_search.meanings) > 0:
            meaning_vi = word_search.meanings[0].meaning_vi or meta_meaning
        else:
            meaning_vi = meta_meaning

        audio_url = word_search.audio_url or get_default_audio_url(word_search.word)

        return VocabularyDetail(
            vocabulary_id=word_search.vocabulary_id,
            word=word_search.word,
            ipa=word_search.ipa or meta_ipa,
            part_of_speech=word_search.part_of_speech or "noun",
            meaning_vi=meaning_vi,
            audio_url=audio_url,
        )

    # If not in DB and auto_create is False (e.g. during realtime scanning), DO NOT write to DB!
    if not auto_create:
        return VocabularyDetail(
            vocabulary_id=None,
            word=meta_word,
            ipa=meta_ipa,
            part_of_speech="noun",
            meaning_vi=meta_meaning,
            audio_url=get_default_audio_url(meta_word),
        )

    # When capturing a photo with confirmed object: Auto-save newly discovered vocabulary to DB
    try:
        new_vocab = Vocabulary(
            word=meta_word,
            ipa=meta_ipa,
            part_of_speech="noun",
            level="BEGINNER",
            audio_url=get_default_audio_url(meta_word),
            created_at=datetime.utcnow()
        )
        db.add(new_vocab)
        db.flush()
        db.add(VocabularyMeaning(vocabulary_id=new_vocab.vocabulary_id, meaning_vi=meta_meaning))
        topic = db.query(Topic).filter(Topic.slug == "objects").first()
        if topic:
            db.execute(vocabulary_topics.insert().values(topic_id=topic.topic_id, vocabulary_id=new_vocab.vocabulary_id))
        db.commit()
        return VocabularyDetail(
            vocabulary_id=new_vocab.vocabulary_id,
            word=new_vocab.word,
            ipa=new_vocab.ipa,
            part_of_speech="noun",
            meaning_vi=meta_meaning,
            audio_url=new_vocab.audio_url,
        )
    except Exception:
        db.rollback()

    return VocabularyDetail(
        vocabulary_id=None,
        word=meta_word,
        ipa=meta_ipa,
        part_of_speech="noun",
        meaning_vi=meta_meaning,
        audio_url=get_default_audio_url(meta_word),
    )


def detect_objects_from_bytes(
    image_bytes: bytes,
    db: Session,
    conf: float = 0.55,
    auto_create_vocab: bool = False
):
    """
    Run YOLO inference on image bytes and enrich with vocabulary info.
    Auto-corrects EXIF rotation for smartphone camera photos.
    Filters out completely blank/flat images (std < 6.0).
    auto_create_vocab: False for realtime scanning (read-only), True for capture.
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

    # Issue 1 Fix: Filter out completely solid/blank images (white, grey, black frames with std < 6.0)
    if float(img.std()) < 6.0:
        return [], width, height

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

            vocab_detail = lookup_vocabulary(db, raw_label, auto_create=auto_create_vocab)

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
    conf: float = 0.55
):
    """
    1. Detect objects using AI (auto_create_vocab=True only if objects are confirmed)
    2. If objects confirmed:
       - Upload image to Cloudinary (folder: app_img_eng)
       - Save image record to PostgreSQL only for authenticated user
    3. Return full response
    """
    # Step 1: Detect objects and create vocab in DB only for confirmed objects
    detections, width, height = detect_objects_from_bytes(
        image_bytes,
        db,
        conf=conf,
        auto_create_vocab=True
    )

    # Step 2 & 3: Only upload to Cloudinary and save to DB when objects ARE ACTUALLY CONFIRMED!
    image_record = None
    secure_url = ""
    if detections:
        secure_url = upload_image_bytes(image_bytes, folder="app_img_eng")
        if user_id is not None:
            image_record = Image(
                user_id=user_id,
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
