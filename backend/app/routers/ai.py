from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.ai import CaptureDetectResponse, RealtimeDetectResponse
from app.services import ai_service
from app.services.ai_detection import MAX_IMAGE_BYTES, InvalidImageError, DetectionUnavailableError
from app.services.cloudinary_service import ImageStorageError

router=APIRouter(prefix="/ai",tags=["AI Object Detection"])

def read_image(file: UploadFile):
    data=file.file.read(MAX_IMAGE_BYTES+1)
    if not data:raise HTTPException(400,"Ảnh đang trống.")
    if len(data)>MAX_IMAGE_BYTES:raise HTTPException(413,"Ảnh vượt quá giới hạn 10 MB.")
    return data

@router.post("/detect/realtime",response_model=RealtimeDetectResponse)
def detect_realtime(file: UploadFile=File(...),conf: float=Query(.55,ge=.1,le=1.0),db: Session=Depends(get_db)):
    """Read-only scanning in the worker pool, without database writes or cloud uploads."""
    data=read_image(file)
    try:
        detections,width,height=ai_service.detect_objects_from_bytes(data,db,conf)
    except InvalidImageError as exc:raise HTTPException(400,str(exc)) from exc
    except DetectionUnavailableError as exc:raise HTTPException(503,str(exc)) from exc
    return {"image_width":width,"image_height":height,"count":len(detections),"detections":detections}

@router.post("/detect/capture",response_model=CaptureDetectResponse)
def detect_and_capture(file: UploadFile=File(...),conf: float=Query(.55,ge=.1,le=1.0),
                       user: User=Depends(get_current_user),db: Session=Depends(get_db)):
    """Validate the account before inference, upload or vocabulary creation."""
    data=read_image(file)
    try:
        return ai_service.capture_and_save(data,user.user_id,db,conf)
    except InvalidImageError as exc:raise HTTPException(400,str(exc)) from exc
    except (DetectionUnavailableError,ImageStorageError) as exc:raise HTTPException(503,str(exc)) from exc
