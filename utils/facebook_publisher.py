import logging
import os
import requests
from typing import Optional

from utils.json_storage import get_trim_settings
from utils.file_utils import file_has_null_byte, repack_image_if_needed, repack_video_if_needed

FB_USER_TOKEN = os.getenv("FB_USER_TOKEN")
FB_API_VERSION = "v22.0"
FB_GRAPH_URL = f"https://graph.facebook.com/{FB_API_VERSION}"

def build_fb_caption(post: dict, chat_id: Optional[int] = None) -> str:
    return post.get("html_text") or post.get("text") or ""

def apply_trim_phrases(post: dict) -> str:
    text = post.get("html_text") or post.get("text") or ""
    text_lines = text.strip().splitlines()

    settings = get_trim_settings(post.get("category", ""), post.get("channel_id"))
    trim_count = settings.get("lines_to_trim", 0)
    phrases = settings.get("trim_phrases", [])

    if trim_count > 0 and phrases and len(text_lines) >= trim_count:
        last_lines = "\n".join(text_lines[-trim_count:])
        if any(p.lower() in last_lines.lower() for p in phrases):
            text_lines = text_lines[:-trim_count]

    return "\n".join(text_lines).strip()

def select_media_for_facebook(post: dict) -> Optional[str]:
    if post["media_type"] == "album":
        if not post.get("media_group"):
            return None
        photos = [m for m in post["media_group"] if "photo" in m["type"]]
        videos = [m for m in post["media_group"] if "video" in m["type"]]
        if photos:
            return "photos"
        elif videos and len(videos) == len(post["media_group"]):
            return "video"
        else:
            return None
    elif post["media_type"] in ["photo", "video"]:
        return post["media_type"]
    return None

def get_facebook_page_title(page_id: str) -> Optional[str]:
    if not FB_USER_TOKEN:
        logging.error("❌ FB_USER_TOKEN не заданий")
        return None
    url = f"{FB_GRAPH_URL}/{page_id}"
    params = {"fields": "name", "access_token": FB_USER_TOKEN}
    try:
        response = requests.get(url, params=params)
        if response.ok:
            return response.json().get("name")
        logging.error(f"❌ Не вдалося отримати назву сторінки Facebook: {response.text}")
    except Exception as e:
        logging.error(f"❌ Виняток при отриманні назви сторінки Facebook: {e}")
    return None

def get_page_token(user_token: str, page_id: str) -> Optional[str]:
    url = f"{FB_GRAPH_URL}/me/accounts"
    params = {"access_token": user_token}
    try:
        response = requests.get(url, params=params)
        if response.ok:
            for page in response.json().get("data", []):
                if page.get("id") == page_id:
                    return page.get("access_token")
        else:
            logging.error(f"❌ get_page_token response error: {response.text}")
            raise Exception(response.json().get("error", {}).get("message", "Unknown error"))
    except Exception as e:
        logging.error(f"❌ Виняток при отриманні токена сторінки: {e}")
        raise Exception(str(e))
    return None

def upload_photo_by_url(photo_url: str, page_id: str, caption: str = "") -> str:
    try:
        page_token = get_page_token(FB_USER_TOKEN, page_id)
        url = f"{FB_GRAPH_URL}/{page_id}/photos"
        params = {
            "access_token": page_token,
            "url": photo_url,
            "caption": caption
        }
        response = requests.post(url, params=params)
        if response.ok:
            return True
        return f"❌ Facebook photo URL upload failed: {response.text}"
    except Exception as e:
        return f"❌ Виняток при upload_photo_by_url: {e}"

def upload_album_by_urls(photo_urls: list[str], page_id: str, caption: str = "") -> str:
    try:
        page_token = get_page_token(FB_USER_TOKEN, page_id)
        attached_media = []
        for url in photo_urls[:10]:
            photo_res = requests.post(
                f"{FB_GRAPH_URL}/{page_id}/photos",
                params={
                    "access_token": page_token,
                    "url": url,
                    "published": "false"
                }
            )
            if photo_res.ok:
                photo_id = photo_res.json().get("id")
                if photo_id:
                    attached_media.append({"media_fbid": photo_id})
            else:
                logging.warning(f"❌ Failed to upload photo for album: {photo_res.text}")

        if not attached_media:
            return "❌ No media uploaded for album."

        feed_url = f"{FB_GRAPH_URL}/{page_id}/feed"
        feed_res = requests.post(
            feed_url,
            params={"access_token": page_token},
            json={
                "message": caption,
                "attached_media": attached_media
            }
        )
        if feed_res.ok:
            return True
        return f"❌ Failed to post album: {feed_res.text}"
    except Exception as e:
        return f"❌ Виняток при upload_album_by_urls: {e}"

def upload_video_by_url(video_url: str, page_id: str, caption: str = "") -> str:
    try:
        page_token = get_page_token(FB_USER_TOKEN, page_id)
        url = f"{FB_GRAPH_URL}/{page_id}/videos"
        params = {
            "access_token": page_token,
            "file_url": video_url,
            "description": caption
        }
        response = requests.post(url, params=params)
        if response.ok:
            return True
        return f"❌ Facebook video upload failed: {response.text}"
    except Exception as e:
        return f"❌ Виняток при upload_video_by_url: {e}"

async def post_to_facebook_text(page_id: str, message: str) -> str:
    try:
        page_token = get_page_token(FB_USER_TOKEN, page_id)
        url = f"{FB_GRAPH_URL}/{page_id}/feed"
        response = requests.post(url, params={"access_token": page_token, "message": message})
        if response.ok:
            logging.debug("✅ Текстовий пост опубліковано")
            return True
        return f"❌ Facebook text post failed: {response.text}"
    except Exception as e:
        return f"❌ Виняток при post_to_facebook_text: {e}"

async def publish_to_facebook(post: dict, page_id: str, client) -> str:
    from utils.facebook_utils import prepare_facebook_post

    if not client:
        return "❌ Відсутній Telethon-клієнт — передай його явно"

    from_chat_id = post.get("from_chat_id")
    if not from_chat_id:
        return "❌ Відсутній from_chat_id у пості"

    try:
        fb_post = await prepare_facebook_post(post, client)
    except Exception as e:
        return f"❌ prepare_facebook_post помилка: {e}"

    if not fb_post:
        return "❌ Підготовка поста завершилась помилкою"

    text = fb_post.get("text", "")
    photo_urls = fb_post.get("photo_urls") or []
    video_url = fb_post.get("video_url")

    logging.debug(f"[publish_to_facebook] text_len={len(text)}, photos={len(photo_urls)}, video_url={'yes' if video_url else 'no'}")

    if photo_urls and len(photo_urls) == 1:
        return upload_photo_by_url(photo_urls[0], page_id, caption=text)
    elif photo_urls and len(photo_urls) > 1:
        return upload_album_by_urls(photo_urls, page_id, caption=text)
    elif video_url:
        return upload_video_by_url(video_url, page_id, caption=text)
    elif text:
        return await post_to_facebook_text(page_id=page_id, message=text)
    else:
        return "❌ Немає контенту для публікації у Facebook"
