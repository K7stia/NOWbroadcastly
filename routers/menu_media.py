import logging
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.state import StatesGroup, State

from utils.json_storage import load_media, save_media
from states.media_states import AddMediaState
from utils.facebook_publisher import get_facebook_page_title
from utils.instagram_publisher import get_instagram_profile_title
from telethon.tl.types import PeerChannel
from utils.telethon_client import client

router = Router()

class AddMediaState(StatesGroup):
    waiting_forward = State()
    waiting_facebook_id = State()
    waiting_instagram_id = State()

@router.callback_query(F.data == "menu_media")
async def menu_media(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Переглянути медіа", callback_data="view_media")],
        [InlineKeyboardButton(text="➕ Додати Telegram-канал", callback_data="add_telegram_channel")],
        [InlineKeyboardButton(text="➕ Додати Facebook-сторінку", callback_data="add_facebook_page")],
        [InlineKeyboardButton(text="➕ Додати Instagram-профіль", callback_data="add_instagram_profile")],
        [InlineKeyboardButton(text="🔄 Оновити медіа", callback_data="refresh_media")],
        [InlineKeyboardButton(text="👥 Групи", callback_data="menu_groups")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    await callback.message.edit_text("📄 Оберіть дію для медіа:", reply_markup=kb)

@router.callback_query(F.data == "view_media")
async def view_media(callback: CallbackQuery):
    media = load_media()
    buttons = []
    PLATFORM_ICONS = {"telegram": "📢", "facebook": "📘", "instagram": "📸"}

    for mid, meta in sorted(media.items()):
        title = meta.get("title") or meta.get("username") or mid
        platform = meta.get("platform", "unknown")
        icon = PLATFORM_ICONS.get(platform, "❔")
        if platform == "telegram":
            known = meta.get("known", False)
            status = "✅" if known else "❌"
            text = f"{icon} {title} {status}"
            callback_data = f"channel_menu|{mid}" if known else f"media_menu|{mid}"
        else:
            text = f"{icon} {title}"
            callback_data = f"media_menu|{mid}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=callback_data)])

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_media")])
    await callback.message.edit_text(
        "🔍 Наші медіа:\n📢 – Telegram канали\n📘 – Facebook сторінки\n📸 – Instagram профілі",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data == "add_telegram_channel")
async def ask_telegram_channel(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddMediaState.waiting_forward)
    await callback.message.edit_text("📥 Перешліть повідомлення з каналу або надішліть @username / ID / посилання на канал")

@router.message(AddMediaState.waiting_forward)
async def handle_telegram_channel(message: Message, state: FSMContext, bot: Bot):
    raw = message.text.strip() if message.text else ""
    logging.debug(f"🟡 Отримано: {raw}")
    input_data, chat_dict, member = None, None, None

    if message.forward_from_chat:
        input_data = str(message.forward_from_chat.id)
        logging.debug(f"📤 Визначено з пересланого повідомлення: {input_data}")
    elif raw.startswith("https://t.me/"):
        extracted = raw.split("https://t.me/")[-1].split("/")[0]
        input_data = extracted.lstrip("@")
        logging.debug(f"🔗 Отримано username з URL: {input_data}")
    elif raw.startswith("@"):
        input_data = raw[1:]
        logging.debug(f"🐦 Отримано username з @: {input_data}")
    elif raw.startswith("-100") and raw[1:].isdigit():
        input_data = raw
        logging.debug(f"🆔 Введено ID у форматі -100: {input_data}")
    elif raw.isdigit():
        input_data = raw
        logging.debug(f"🔢 Введено простий числовий ID: {input_data}")

    if not input_data:
        logging.warning("❌ Не вдалося розпізнати канал.")
        await message.answer("❌ Не вдалося розпізнати канал.")
        return

    try:
        logging.debug(f"🤖 Пробуємо bot.get_chat({input_data})")
        chat = await bot.get_chat(input_data)
        member = await bot.get_chat_member(chat.id, bot.id)
        logging.debug(f"✅ Отримано через бот API: {chat.title} | ID: {chat.id}")
        chat_dict = {
            "id": chat.id,
            "username": f"@{chat.username}" if chat.username else None,
            "title": chat.title or f"ID {chat.id}"
        }
    except Exception as bot_error:
        logging.warning(f"⚠️ bot.get_chat не вдався: {bot_error}")
        try:
            logging.debug("📡 Запускаємо Telethon fallback...")
            await client.start()

            if input_data.startswith("-100"):
                peer = PeerChannel(int(input_data[4:]))
            elif input_data.isdigit():
                peer = PeerChannel(int(input_data))
            else:
                peer = input_data

            entity = await client.get_entity(peer)
            logging.debug(f"✅ Telethon entity знайдено: {getattr(entity, 'title', '?')} | ID: {entity.id}")
            channel_id = int(f"-100{entity.id}") if entity.id > 0 else entity.id
            chat_dict = {
                "id": channel_id,
                "username": f"@{getattr(entity, 'username', '')}" if getattr(entity, "username", None) else None,
                "title": getattr(entity, "title", f"ID {channel_id}")
            }
        except Exception as telethon_error:
            logging.error(f"❌ Telethon fallback не вдався: {telethon_error}")
            await message.answer(f"❌ Не вдалося отримати інформацію про канал (Telethon): {telethon_error}")
            return

    if member and member.status not in ("administrator", "creator"):
        logging.warning(f"❌ Бот є учасником, але не адмін: {member.status}")
        await message.answer("❌ Бот не є адміністратором цього каналу.")
        return

    media_id = str(chat_dict["id"])
    entry = {
        "id": chat_dict["id"],
        "username": chat_dict.get("username"),
        "title": chat_dict.get("title") or media_id,
        "platform": "telegram",
        "known": bool(member)
    }

    logging.info(f"✅ Додаємо канал: {entry}")
    media = load_media()
    media[media_id] = entry
    save_media(media)

    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 До списку медіа", callback_data="view_media")],
        [InlineKeyboardButton(text="🏠 Головне меню", callback_data="back_main")]
    ])
    await message.answer(f"✅ Telegram-канал <b>{entry['title']}</b> додано.", parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data == "add_facebook_page")
async def ask_facebook_page(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddMediaState.waiting_facebook_id)
    await callback.message.edit_text("🔗 Введіть Facebook Page ID:")

@router.message(AddMediaState.waiting_facebook_id)
async def handle_facebook_page_id(message: Message, state: FSMContext):
    page_id = message.text.strip()
    title = get_facebook_page_title(page_id)
    if not title:
        await message.answer("❌ Не вдалося знайти назву сторінки за цим ID.")
        return

    entry = {"id": page_id, "username": None, "title": title, "platform": "facebook"}
    media = load_media()
    media[page_id] = entry
    save_media(media)

    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 До списку медіа", callback_data="view_media")],
        [InlineKeyboardButton(text="🏠 Головне меню", callback_data="back_main")]
    ])
    await message.answer(f"✅ Facebook-сторінку <b>{title}</b> додано.", parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("media_menu|"))
async def media_menu(callback: CallbackQuery):
    media_id = callback.data.split("|", 1)[1]
    media = load_media()
    meta = media.get(media_id)
    if not meta:
        await callback.message.edit_text("❌ Медіа не знайдено.")
        return

    title = meta.get("title") or meta.get("username") or media_id
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Видалити", callback_data=f"delete_media_confirm|{media_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="view_media")]
    ])
    await callback.message.edit_text(f"⚙️ Керування медіа:\n<b>{title}</b>", parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("delete_media_confirm|"))
async def confirm_delete_media(callback: CallbackQuery):
    media_id = callback.data.split("|", 1)[1]
    media = load_media()
    meta = media.get(media_id)
    title = meta.get("title") or meta.get("username") or media_id
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Так, видалити", callback_data=f"delete_media_final|{media_id}")],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="view_media")]
    ])
    await callback.message.edit_text(f"⚠️ Ви впевнені, що хочете видалити <b>{title}</b>?", parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("delete_media_final|"))
async def delete_media_final(callback: CallbackQuery):
    media_id = callback.data.split("|", 1)[1]
    media = load_media()
    if media_id in media:
        del media[media_id]
        save_media(media)
        await callback.message.edit_text("✅ Медіа успішно видалено.")
    else:
        await callback.message.edit_text(f"⚠️ Медіа <code>{media_id}</code> не знайдено.", parse_mode="HTML")

@router.callback_query(F.data == "refresh_media")
async def refresh_media(callback: CallbackQuery, bot: Bot):
    media = load_media()
    updated = 0

    for mid, meta in media.items():
        if meta.get("platform") != "telegram":
            continue
        try:
            chat = await bot.get_chat(int(mid))
            member = await bot.get_chat_member(chat.id, bot.id)
            if member.status in ("administrator", "creator"):
                meta["known"] = True
                updated += 1
            else:
                meta.pop("known", None)
        except Exception:
            meta.pop("known", None)

    save_media(media)
    text = f"✅ Оновлено: {updated} каналів із правами адміністратора."
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 До меню медіа", callback_data="menu_media")],
        [InlineKeyboardButton(text="🏠 Головне меню", callback_data="back_main")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)

@router.callback_query(F.data == "add_instagram_profile")
async def ask_instagram_profile(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddMediaState.waiting_instagram_id)
    await callback.message.edit_text("🔗 Введіть Facebook Page ID, до якого прив'язаний Instagram-профіль:")

@router.message(AddMediaState.waiting_instagram_id)
async def handle_instagram_profile_id(message: Message, state: FSMContext):
    page_id = message.text.strip()
    title = get_instagram_profile_title(page_id)

    if not title:
        await message.answer("❌ Не вдалося знайти Instagram-профіль за цим Page ID.")
        return

    entry = {
        "id": page_id,
        "username": None,
        "title": title,
        "platform": "instagram"
    }
    media = load_media()
    media[page_id] = entry
    save_media(media)

    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 До списку медіа", callback_data="view_media")],
        [InlineKeyboardButton(text="🏠 Головне меню", callback_data="back_main")]
    ])
    await message.answer(f"✅ Instagram-профіль <b>{title}</b> додано.", parse_mode="HTML", reply_markup=kb)
