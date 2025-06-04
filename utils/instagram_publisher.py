import logging
import os
import requests
import asyncio
from typing import Optional

from utils.instagram_utils import prepare_instagram_post

IG_USER_TOKEN = os.getenv("FB_USER_TOKEN")
FB_API_VERSION = "v22.0"
FB_GRAPH_URL = f"https://graph.facebook.com/{FB_API_VERSION}"


def get_instagram_account_id(fb_page_id: str) -> Optional[str]:
    url = f"{FB_GRAPH_URL}/{fb_page_id}"
    params = {
        "fields": "instagram_business_account",
        "access_token": IG_USER_TOKEN
    }
    try:
        response = requests.get(url, params=params)
        if response.ok:
            ig_data = response.json().get("instagram_business_account", {})
            return ig_data.get("id")
        logging.error(f"❌ Не вдалося отримати IG ID: {response.text}")
    except Exception as e:
        logging.error(f"❌ Виняток при отриманні IG ID: {e}")
    return None


def create_media_container(media_url: str, ig_account_id: str, caption: str = "", is_video: bool = False) -> Optional[str]:
    url = f"{FB_GRAPH_URL}/{ig_account_id}/media"
    payload = {
        "access_token": IG_USER_TOKEN,
        "caption": caption,
        "media_type": "VIDEO" if is_video else "IMAGE"
    }
    payload["video_url" if is_video else "image_url"] = media_url

    try:
        response = requests.post(url, data=payload)
        if response.ok:
            return response.json().get("id")
        raise Exception(response.text)
    except Exception as e:
        raise Exception(f"❌ Створення контейнера Instagram: {e}")


def publish_container(container_id: str, ig_account_id: str) -> bool:
    url = f"{FB_GRAPH_URL}/{ig_account_id}/media_publish"
    payload = {
        "access_token": IG_USER_TOKEN,
        "creation_id": container_id
    }
    try:
        response = requests.post(url, data=payload)
        if response.ok:
            logging.debug("✅ IG пост опубліковано")
            return True
        raise Exception(response.text)
    except Exception as e:
        raise Exception(f"❌ Публікація Instagram контейнера: {e}")


def upload_to_instagram(page_id: str, media_url: str, caption: str = "", is_video: bool = False) -> str:
    try:
        ig_account_id = get_instagram_account_id(page_id)
        if not ig_account_id:
            return "❌ Не знайдено Instagram акаунт для цієї сторінки"

        container_id = create_media_container(media_url, ig_account_id, caption, is_video=is_video)
        if not container_id:
            return "❌ Створення контейнера Instagram не вдалося"

        publish_container(container_id, ig_account_id)
        return True
    except Exception as e:
        return str(e)


def upload_instagram_photo(page_id: str, photo_url: str, caption: str = "") -> str:
    return upload_to_instagram(page_id, media_url=photo_url, caption=caption, is_video=False)


def upload_instagram_video(page_id: str, video_url: str, caption: str = "") -> str:
    return upload_to_instagram(page_id, media_url=video_url, caption=caption, is_video=True)


MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 3


async def publish_to_instagram(post: dict, page_id: str, client) -> str:
    if not client:
        return "❌ Відсутній Telethon-клієнт — передай явно"

    if not page_id:
        return "❌ Відсутній page_id для Instagram"

    insta_post = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            insta_post = await prepare_instagram_post(post, client)
        except Exception as e:
            return f"❌ prepare_instagram_post помилка (спроба {attempt}): {e}"

        if not insta_post:
            return f"⚠️ prepare_instagram_post повернув None (спроба {attempt})"

        photo_urls = insta_post.get("photo_urls") or []
        video_url = insta_post.get("video_url")
        text = (insta_post.get("text") or "").strip()

        logging.debug(
            f"[publish_to_instagram] 📦 Спроба {attempt}: "
            f"text_len={len(text)}, photo_urls={photo_urls}, video_url={video_url}"
        )

        if photo_urls or video_url:
            break
        elif attempt < MAX_RETRIES:
            logging.info(f"⏳ Медіа ще не готове, очікування {RETRY_DELAY_SECONDS}s...")
            await asyncio.sleep(RETRY_DELAY_SECONDS)

    if not insta_post or (not photo_urls and not video_url):
        return "⚠️ Немає валідного медіа для публікації після всіх спроб"

    try:
        if photo_urls and len(photo_urls) == 1:
            return upload_instagram_photo(page_id, photo_urls[0], caption=text)
        elif video_url:
            return upload_instagram_video(page_id, video_url, caption=text)
        else:
            return "⚠️ Неочікувана ситуація без медіа"
    except Exception as e:
        return f"❌ Помилка при публікації в Instagram: {e}"


def get_instagram_profile_title(page_id: str) -> Optional[str]:
    url_ig = f"{FB_GRAPH_URL}/{page_id}"
    params = {
        "fields": "instagram_business_account",
        "access_token": IG_USER_TOKEN
    }
    try:
        res_ig = requests.get(url_ig, params=params)
        if not res_ig.ok:
            logging.error(f"❌ Не вдалося отримати IG ID: {res_ig.text}")
            return None
        ig_id = res_ig.json().get("instagram_business_account", {}).get("id")
        if not ig_id:
            return None
    except Exception as e:
        logging.error(f"❌ Виняток при отриманні IG ID: {e}")
        return None

    url_profile = f"{FB_GRAPH_URL}/{ig_id}"
    params = {
        "fields": "name,username",
        "access_token": IG_USER_TOKEN
    }
    try:
        res_profile = requests.get(url_profile, params=params)
        if res_profile.ok:
            data = res_profile.json()
            return data.get("name") or f"@{data.get('username')}" or f"IG:{ig_id}"
        logging.error(f"❌ Не вдалося отримати профіль IG: {res_profile.text}")
    except Exception as e:
        logging.error(f"❌ Виняток при отриманні IG профілю: {e}")
    return None
