from pydantic import BaseModel


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class VocabularyDetail(BaseModel):
    vocabulary_id: int | None = None
    word: str
    ipa: str | None = None
    part_of_speech: str | None = None
    meaning_vi: str | None = None
    audio_url: str | None = None


class DetectionItem(BaseModel):
    label: str
    confidence: float
    box: BoundingBox
    vocabulary: VocabularyDetail


class RealtimeDetectResponse(BaseModel):
    image_width: int
    image_height: int
    count: int
    detections: list[DetectionItem]


class CaptureDetectResponse(BaseModel):
    image_id: int | None = None
    image_url: str
    image_width: int
    image_height: int
    count: int
    detections: list[DetectionItem]
