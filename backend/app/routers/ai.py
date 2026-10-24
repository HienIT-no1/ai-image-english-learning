from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.auth import get_optional_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.ai import CaptureDetectResponse, RealtimeDetectResponse
from app.services import ai_service

router = APIRouter(
    prefix="/ai",
    tags=["AI Object Detection"]
)


@router.post("/detect/realtime", response_model=RealtimeDetectResponse)
async def detect_realtime(
    file: UploadFile = File(..., description="Camera frame image"),
    conf: float = Query(0.35, ge=0.1, le=1.0, description="Confidence threshold"),
    db: Session = Depends(get_db)
):
    """
    Realtime camera frame detection:
    - Runs YOLO inference (best.pt)
    - Returns bounding boxes + vocabulary + pronunciation audio
    - Optimized for speed (no upload, no DB save)
    """
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty image file")

    try:
        detections, width, height = ai_service.detect_objects_from_bytes(
            image_bytes=image_bytes,
            db=db,
            conf=conf
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Image processing failed: {str(e)}")

    return {
        "image_width": width,
        "image_height": height,
        "count": len(detections),
        "detections": detections,
    }


@router.post("/detect/capture", response_model=CaptureDetectResponse)
async def detect_and_capture(
    file: UploadFile = File(..., description="Captured camera photo"),
    conf: float = Query(0.35, ge=0.1, le=1.0, description="Confidence threshold"),
    user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Captured photo workflow:
    1. AI YOLO (best.pt) detection -> Bounding boxes & words
    2. Upload image to Cloudinary (folder: app_img_eng)
    3. Save secure_url to PostgreSQL (images table)
    4. Return full info for display & future features
    """
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty image file")

    try:
        user_id = user.user_id if user else None
        result = ai_service.capture_and_save(
            image_bytes=image_bytes,
            user_id=user_id,
            db=db,
            conf=conf
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Detection and upload failed: {str(e)}")
