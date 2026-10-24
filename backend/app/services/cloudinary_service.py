import io
import cloudinary
import cloudinary.uploader
from app.core.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)


def upload_image_bytes(image_bytes: bytes, folder: str = "app_img_eng") -> str:
    """
    Upload image bytes to Cloudinary and return secure URL.
    """
    response = cloudinary.uploader.upload(
        io.BytesIO(image_bytes),
        folder=folder,
        resource_type="image"
    )
    return response.get("secure_url")
