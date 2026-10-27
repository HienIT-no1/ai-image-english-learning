import logging
import urllib.parse
from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from app.models.image import Image
from app.models.topic import Topic, vocabulary_topics
from app.models.user import User
from app.models.vocabulary import Vocabulary, VocabularyMeaning
from app.schemas.ai import BoundingBox, DetectionItem, VocabularyDetail
from app.services.ai_detection import decode_image, detect_candidates
from app.services.cloudinary_service import upload_image_bytes, delete_uploaded_image, ImageStorageError

logger=logging.getLogger(__name__)

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
    return f"https://dict.youdao.com/dictvoice?audio={urllib.parse.quote_plus(word)}&type=2"


def lookup_vocabulary(db: Session, raw_label: str, auto_create: bool=False) -> VocabularyDetail:
    key=raw_label.strip().lower()
    canonical,ipa,meaning=LABEL_METADATA.get(key,(raw_label.replace("_"," ").strip(),None,raw_label.replace("_"," ").strip()))
    # A computer mouse is a distinct sense; never fall back to the animal's ID.
    candidates=[canonical] if key=="mouse" else list(dict.fromkeys([canonical,raw_label,raw_label.replace("_"," ").strip()]))
    word=None
    for candidate in candidates:
        word=db.scalar(select(Vocabulary).where(func.lower(Vocabulary.word)==candidate.lower()))
        if word is not None:break
    if word is None and auto_create:
        ident=db.scalar(insert(Vocabulary).values(word=canonical,ipa=ipa,part_of_speech="noun",level="BEGINNER",
                audio_url=get_default_audio_url(canonical),created_at=datetime.now(timezone.utc))
                .on_conflict_do_nothing(index_elements=["word"]).returning(Vocabulary.vocabulary_id))
        word=db.scalar(select(Vocabulary).where(Vocabulary.word==canonical))
        if ident is not None:
            db.add(VocabularyMeaning(vocabulary_id=ident,meaning_vi=meaning))
            topic=db.scalar(select(Topic).where(Topic.slug=="objects"))
            if topic is not None:
                db.execute(insert(vocabulary_topics).values(vocabulary_id=ident,topic_id=topic.topic_id).on_conflict_do_nothing())
            db.flush()
        # No commit here: the caller owns the complete capture transaction.
    if word is None:
        return VocabularyDetail(vocabulary_id=None,word=canonical,ipa=ipa,part_of_speech="noun",
                                meaning_vi=meaning,audio_url=get_default_audio_url(canonical))
    return VocabularyDetail(vocabulary_id=word.vocabulary_id,word=word.word,ipa=word.ipa or ipa,
            part_of_speech=word.part_of_speech or "noun",
            meaning_vi=(word.meanings[0].meaning_vi if word.meanings else None) or meaning,
            audio_url=word.audio_url or get_default_audio_url(word.word))


def sync_model_labels_to_db(db: Session):
    """Explicit seed helper; existing animal meanings are never rewritten."""
    try:
        for label in LABEL_METADATA:lookup_vocabulary(db,label,auto_create=True)
        db.commit()
    except Exception:
        db.rollback();raise


def detect_objects_from_bytes(image_bytes: bytes, db: Session, conf: float=.55):
    image=decode_image(image_bytes)
    height,width=image.shape[:2]
    detections=[DetectionItem(label=c.label,confidence=round(c.confidence,3),
        box=BoundingBox(x1=round(c.box[0],2),y1=round(c.box[1],2),x2=round(c.box[2],2),y2=round(c.box[3],2)),
        vocabulary=lookup_vocabulary(db,c.label)) for c in detect_candidates(image,conf)]
    return detections,width,height


def capture_and_save(image_bytes: bytes, user_id: int, db: Session, conf: float=.55):
    if not user_id or db.get(User,user_id) is None:
        raise PermissionError("A valid user is required to save a capture")
    # Validation and inference are read-only, including vocabulary lookup.
    detections,width,height=detect_objects_from_bytes(image_bytes,db,conf)
    response={"image_id":None,"image_url":"","image_width":width,"image_height":height,
              "count":len(detections),"detections":detections}
    if not detections:return response
    try:
        asset=upload_image_bytes(image_bytes,folder="app_img_eng")
    except Exception:
        db.rollback();raise
    try:
        for detection in detections:
            detection.vocabulary=lookup_vocabulary(db,detection.label,auto_create=True)
        image=Image(user_id=user_id,image_url=asset.url,source_type="CAMERA")
        db.add(image);db.flush()
        response.update(image_id=image.image_id,image_url=image.image_url)
        db.commit()
        return response
    except Exception as exc:
        db.rollback()
        try:
            delete_uploaded_image(asset.public_id)
        except Exception:
            logger.error("Could not compensate failed capture upload: %s",asset.public_id)
        raise ImageStorageError("Chưa lưu được ảnh. Vui lòng thử lại sau.") from exc
