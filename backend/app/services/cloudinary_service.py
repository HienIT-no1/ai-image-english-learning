import io
from dataclasses import dataclass
import cloudinary
import cloudinary.uploader
from app.core.config import settings

cloudinary.config(cloud_name=settings.CLOUDINARY_CLOUD_NAME,api_key=settings.CLOUDINARY_API_KEY,
                  api_secret=settings.CLOUDINARY_API_SECRET,secure=True)

class ImageStorageError(RuntimeError):
    pass

@dataclass(frozen=True)
class UploadedImage:
    url: str
    public_id: str

def delete_uploaded_image(public_id: str):
    result=cloudinary.uploader.destroy(public_id,invalidate=True,resource_type="image")
    if result.get("result") not in ("ok","not found"):
        raise ImageStorageError("Không thể dọn ảnh tải lên chưa hoàn tất.")

def upload_image_bytes(image_bytes: bytes,folder: str="app_img_eng") -> UploadedImage:
    if not all((settings.CLOUDINARY_CLOUD_NAME,settings.CLOUDINARY_API_KEY,settings.CLOUDINARY_API_SECRET)):
        raise ImageStorageError("Dịch vụ lưu ảnh chưa sẵn sàng. Vui lòng thử lại sau.")
    try:
        result=cloudinary.uploader.upload(io.BytesIO(image_bytes),folder=folder,resource_type="image",timeout=10)
        public_id,url=result.get("public_id"),result.get("secure_url")
        if not public_id or not url or not url.startswith("https://"):
            if public_id:delete_uploaded_image(public_id)
            raise ImageStorageError("Máy chủ lưu ảnh chưa trả kết quả hợp lệ.")
        return UploadedImage(url=url,public_id=public_id)
    except ImageStorageError:
        raise
    except Exception as exc:
        raise ImageStorageError("Không tải ảnh lên được. Vui lòng thử lại sau.") from exc
