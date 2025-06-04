from io import BytesIO
import tempfile
import logging
import os
import hashlib
from typing import Optional, Union
from telethon import TelegramClient
from aiogram import Bot
from aiogram.types import Message as AiogramMessage
from telethon.tl.types import Message as TelethonMessage, MessageMediaPhoto, MessageMediaDocument
from utils.file_utils import file_has_null_byte, repack_image_if_needed, repack_video_if_needed

async def get_media_bytes(
    *,
    bot: Optional[Bot] = None,
    telethon: Optional[TelegramClient] = None,
    message: Union[AiogramMessage, TelethonMessage],
    file_type: str = "photo"
) -> Optional[BytesIO]:
    logging.debug(f"[get_media_bytes] Початок. file_type={file_type}")

    if isinstance(message, AiogramMessage) and bot:
        file_id = None
        if file_type == "photo" and message.photo:
            file_id = message.photo[-1].file_id
        elif file_type == "video" and message.video:
            file_id = message.video.file_id

        if not file_id:
            logging.warning("[get_media_bytes] ❌ Немає photo/video в AiogramMessage")
            return None

        try:
            logging.debug(f"[get_media_bytes] Bot API file_id: {file_id}")
            file = await bot.get_file(file_id)
            file_path = file.file_path
            file_data = await bot.download_file(file_path)
            logging.debug(f"[get_media_bytes] ✅ Отримано файл {file_path}, розмір: {len(file_data)} байт")
            return BytesIO(file_data)
        except Exception as e:
            logging.error(f"[get_media_bytes] ❌ Помилка при завантаженні через Bot API: {e}")
            return None

    elif isinstance(message, TelethonMessage) and telethon:
        if not (message.photo or message.video):
            logging.warning("[get_media_bytes] ❌ Немає медіа в TelethonMessage")
            return None

        suffix = ".jpg" if message.photo else ".mp4"
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                await telethon.download_media(message, file=tmp.name)
                with open(tmp.name, "rb") as f:
                    data = f.read()
                logging.debug(f"[get_media_bytes] ✅ Telethon: файл {tmp.name}, розмір: {len(data)} байт")
                return BytesIO(data)
        except Exception as e:
            logging.error(f"[get_media_bytes] ❌ Помилка при завантаженні через Telethon: {e}")
            return None

    logging.warning("[get_media_bytes] ❌ Непідтримуваний тип повідомлення або відсутній бот/клієнт")
    return None

async def download_file_from_telegram(client, file_info: dict) -> Optional[str]:
    from_chat_id = file_info["from_chat_id"]
    message_id = file_info["message_id"]

    message = await client.get_messages(from_chat_id, ids=message_id)
    if not message or not message.media:
        logging.warning("⚠️ [download_file_from_telegram] No media found")
        return None

    suffix = ".jpg"
    if isinstance(message.media, MessageMediaDocument):
        mime_type = message.file.mime_type or ""
        if "video" in mime_type:
            suffix = ".mp4"
        elif "image" in mime_type:
            suffix = ".jpg"
        else:
            suffix = ".bin"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        path = tmp_file.name

    await client.download_media(message, file=path)
    logging.debug(f"[download_file_from_telegram] ✅ Завантажено файл: {path}")

    try:
        with open(path, "rb") as f:
            content = f.read()
            h = hashlib.md5(content).hexdigest()
            logging.debug(f"[download_file_from_telegram] 📏 Розмір: {len(content)} байт, md5: {h}")
    except Exception as e:
        logging.warning(f"[download_file_from_telegram] ❌ Error reading file: {e}")
        return None

    # 🔍 Перевірка на null byte + репак
    if file_has_null_byte(path):
        logging.debug(f"[download_file_from_telegram] ⚠️ Null byte виявлено — пробуємо репак")
        if suffix == ".jpg":
            new_path = repack_image_if_needed(path)
        elif suffix == ".mp4":
            new_path = repack_video_if_needed(path)
        else:
            new_path = None

        if new_path:
            logging.debug(f"[download_file_from_telegram] ✅ Репак завершено: {new_path}")
            return new_path
        else:
            logging.error(f"[download_file_from_telegram] ❌ Не вдалося репакнути файл {path}")
            return None

    return path

async def download_message_media(from_chat_id: Union[int, str], message_id: int) -> Optional[str]:
    logging.warning("⚠️ download_message_media ще не реалізована")
    return None
