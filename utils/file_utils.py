import os
import tempfile
import subprocess
import requests
from PIL import Image
import logging
import cloudinary
import cloudinary.uploader


cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def clean_with_pillow(path: str) -> str | None:
    try:
        img = Image.open(path)
        rgb = img.convert("RGB")
        clean_fd, clean_path = tempfile.mkstemp(suffix=".jpg")
        os.close(clean_fd)
        rgb.save(clean_path, format="JPEG", quality=95)
        logging.debug(f"[clean_with_pillow] ✅ Saved Pillow-cleaned file: {clean_path}")
        return clean_path
    except Exception as e:
        logging.warning(f"❌ clean_with_pillow error: {e}")
        return None

def repack_image_if_needed(image_path: str) -> str | None:
    try:
        logging.debug(f"[repack_image_if_needed] ☁️ Uploading to Cloudinary: {image_path}")
        upload_result = cloudinary.uploader.upload(image_path, resource_type="image")
        secure_url = upload_result.get("secure_url")
        if not secure_url:
            logging.error(f"❌ Cloudinary upload failed: {upload_result}")
            return None

        logging.debug(f"[repack_image_if_needed] ✅ Cloudinary URL: {secure_url}")
        return secure_url

    except Exception as e:
        logging.error(f"❌ Cloudinary repack error: {e}")
        return None

def repack_video_if_needed(video_path: str) -> str | None:
    try:
        logging.debug(f"[repack_video_if_needed] ☁️ Uploading to Cloudinary: {video_path}")
        upload_result = cloudinary.uploader.upload(video_path, resource_type="video")
        secure_url = upload_result.get("secure_url")
        if not secure_url:
            logging.error(f"❌ Cloudinary video upload failed: {upload_result}")
            return None
        logging.debug(f"[repack_video_if_needed] ✅ Cloudinary video URL: {secure_url}")
        return secure_url
    except Exception as e:
        logging.error(f"❌ Cloudinary video repack error: {e}")
        return None

def file_has_null_byte(path: str) -> bool:
    """Перевіряє, чи файл має null byte у критичних мета-даних.
    Для JPEG-файлів null bytes дозволяються — Facebook їх приймає."""
    if path.lower().endswith(".jpg") or path.lower().endswith(".jpeg"):
        return False  # дозволяємо null байти в JPEG — вони допустимі

    try:
        with open(path, "rb") as f:
            data = f.read()
        return b"\x00" in data
    except Exception as e:
        # якщо щось пішло не так — логіка безпечності
        return True

def extract_file_id(msg) -> object | None:
    try:
        if hasattr(msg, "photo") and msg.photo:
            return msg.photo
        if hasattr(msg, "video") and msg.video:
            return msg.video
        if hasattr(msg, "document") and msg.document:
            return msg.document
    except Exception as e:
        import logging
        logging.warning(f"[extract_file_id] ⚠️ Не вдалося отримати file object: {e}")
    return None
