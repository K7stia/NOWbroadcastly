import logging
import re
import hashlib
import io
import mimetypes
from PIL import Image
from utils.download import download_file_from_telegram
from utils.json_storage import get_trim_settings
from utils.file_utils import file_has_null_byte, repack_image_if_needed, repack_video_if_needed

logger = logging.getLogger(__name__)

def strip_html_tags(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text)

def should_trim(text_lines, trim_count, trim_phrases):
    if trim_count > 0 and trim_phrases and len(text_lines) >= trim_count:
        last_lines = "\n".join(text_lines[-trim_count:])
        return any(p.lower() in last_lines.lower() for p in trim_phrases)
    return False

#def file_has_null_byte(path: str) -> bool:
#    try:
#        with open(path, "rb") as f:
#            content = f.read()
#            if b"\x00" in content:
#                logging.debug(f"[file_has_null_byte] ⚠️ Null byte виявлено в {path}")
#                return True
#            return False
#    except Exception as e:
#        logging.warning(f"[file_has_null_byte] ❌ Помилка при читанні {path}: {e}")
#        return True

# def repack_image_if_needed(image_path: str) -> bytes | None:
#     try:
#         with Image.open(image_path) as img:
#             with io.BytesIO() as output:
#                 img.convert("RGB").save(output, format="JPEG", quality=95)
#                 return output.getvalue()
#     except Exception as e:
#         logging.error(f"❌ repack_image_if_needed error: {e}")
#         return None

def get_mime_type(path: str) -> str:
    mime_type, _ = mimetypes.guess_type(path)
    return mime_type or ""

async def prepare_facebook_post(post: dict, client=None) -> dict:
    logging.debug(f"[prepare_facebook_post] Start. Raw post keys: {list(post.keys())}")
    logging.debug(f"[prepare_facebook_post] media_type={post.get('media_type')}, from_chat_id={post.get('from_chat_id')}")

    if post.get("media_type") == "album" and not post.get("text") and not post.get("html_text"):
        for m in post.get("media_group", []):
            if m.get("text"):
                post["text"] = m["text"]
                break
            if m.get("html_text"):
                post["html_text"] = m["html_text"]
                break

    text = post.get("html_text", "") or post.get("text", "")
    text_lines = text.strip().splitlines()

    if "category" in post and "original_chat_id" in post:
        channel_id_for_trim = -1 * (1000000000000 + abs(int(post["original_chat_id"])))
        trim_settings = get_trim_settings(post["category"], channel_id_for_trim)
        trim_count = trim_settings.get("lines_to_trim", 0)
        trim_phrases = trim_settings.get("trim_phrases", [])
        if should_trim(text_lines, trim_count, trim_phrases):
            text_lines = text_lines[:-trim_count]

    cleaned_text = strip_html_tags("\n".join(text_lines).strip())
    media_type = post.get("media_type")
    media_group = post.get("media_group", [])
    from_chat_id = post.get("from_chat_id")
    photo_urls = []
    video_url = None

    if not client:
        return {
            "text": cleaned_text,
            "photo_urls": None,
            "video_url": None,
            "from_chat_id": from_chat_id
        }

    if media_type == "album":
        photo_items = []
        video_items = []

        for m in media_group:
            msg_id = m.get("message_id")
            if not msg_id:
                continue

            path = await download_file_from_telegram(client, {
                "from_chat_id": from_chat_id,
                "message_id": msg_id
            })

            mime = get_mime_type(path)
            if mime.startswith("image/"):
                photo_items.append((m, path))
            elif mime.startswith("video/"):
                video_items.append((m, path))

        logging.debug(f"[prepare_facebook_post] album: {len(photo_items)} photo(s), {len(video_items)} video(s)")

        if len(photo_items) >= len(video_items):
            for _, path in photo_items[:10]:
                new_path = repack_image_if_needed(path)
                if new_path:
                    photo_urls.append(new_path)
        elif video_items:
            _, path = video_items[0]
            video_url = repack_video_if_needed(path)

    elif media_type == "photo":
        msg_id = post.get("message_id")
        path = await download_file_from_telegram(client, {
            "from_chat_id": from_chat_id,
            "message_id": msg_id
        })
        new_path = repack_image_if_needed(path)
        if new_path:
            photo_urls.append(new_path)

    elif media_type == "video":
        msg_id = post.get("message_id")
        path = await download_file_from_telegram(client, {
            "from_chat_id": from_chat_id,
            "message_id": msg_id
        })
        video_url = repack_video_if_needed(path)

    return {
        "text": cleaned_text,
        "photo_urls": photo_urls or None,
        "video_url": video_url,
        "from_chat_id": from_chat_id
    }
