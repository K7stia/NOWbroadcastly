import html
import re
import logging
from typing import Optional

from utils.download import download_file_from_telegram
from utils.file_utils import file_has_null_byte, repack_image_if_needed, repack_video_if_needed

async def prepare_instagram_post(post: dict, client) -> Optional[dict]:
    media_type = post.get("media_type")
    media_group = post.get("media_group", [])
    file_object = post.get("file_object")

    # 💬 очищення тексту
    text = post.get("html_text") or post.get("text") or ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text).strip()

    photo_urls = []
    video_url = None

    try:
        logging.debug(f"[prepare_instagram_post] 🔎 media_type={media_type}, file_object={bool(file_object)}")

        # 📸 Якщо є готовий URL
        if post.get("photo_url"):
            logging.debug(f"[prepare_instagram_post] ✅ Виявлено photo_url: {post['photo_url']}")
            return {
                "text": text,
                "photo_urls": [post["photo_url"]],
                "video_url": None
            }

        if not client:
            logging.warning("[prepare_instagram_post] ⚠️ Клієнт не передано — повертаємо лише текст")
            return {"text": text}

        # ✅ Якщо є file_object (фото або відео)
        if media_type in ["photo", "video"] and file_object:
            file = await client.download_media(file_object)
            if not file or file_has_null_byte(file):
                logging.warning(f"[prepare_instagram_post] ⚠️ Проблема з файлом: {file}")
                return {"text": text}

            if media_type == "photo":
                url = repack_image_if_needed(file)
                if url:
                    photo_urls.append(url)
            elif media_type == "video":
                url = repack_video_if_needed(file)
                if url:
                    video_url = url

        # 🧩 fallback для album — беремо перше валідне фото/відео
        elif media_type == "album" and media_group:
            for m in media_group:
                if not m.get("file_object"):
                    continue
                logging.debug(f"[album] ➕ Обробка медіа: {m.get('type')}")
                file = await client.download_media(m["file_object"])
                if not file or file_has_null_byte(file):
                    logging.warning(f"[album] ❌ Проблема з файлом: {file}")
                    continue

                if "photo" in m["type"]:
                    url = repack_image_if_needed(file)
                    if url:
                        photo_urls.append(url)
                    break
                elif "video" in m["type"]:
                    url = repack_video_if_needed(file)
                    if url:
                        video_url = url
                    break

        logging.debug(f"[prepare_instagram_post] ✅ Підсумок: photo_urls={photo_urls}, video_url={video_url}")
        return {
            "text": text,
            "photo_urls": photo_urls or None,
            "video_url": video_url
        }

    except Exception as e:
        logging.exception(f"❌ prepare_instagram_post: виняток: {e}")
        return None
