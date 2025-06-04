from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.state import StatesGroup, State
from utils.json_storage import load_channels, load_known_channels, save_known_channels, save_channels
from states.add_channel import AddChannelState

# Telethon
from utils.telethon_fetcher import resolve_channel_by_username

router = Router()

@router.callback_query(F.data == "menu_channels")
async def menu_channels(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Переглянути канали", callback_data="view_channels")],
        [InlineKeyboardButton(text="➕ Додати канал", callback_data="add_channel")],
        [InlineKeyboardButton(text="🔄 Оновити канали", callback_data="refresh_channels")],
        [InlineKeyboardButton(text="👥 Групи каналів", callback_data="menu_groups")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    await callback.message.edit_text("📄 Оберіть дію для каналів:", reply_markup=kb)


@router.callback_query(F.data == "view_channels")
async def view_channels(callback: CallbackQuery):
    channels = load_channels()
    known = load_known_channels()

    all_ids = set(channels.keys()) | set(known.keys())
    buttons = []

    for channel_id in sorted(all_ids):
        meta = channels.get(channel_id) or known.get(channel_id)
        if not meta:
            continue
        title = meta.get("title") or meta.get("username") or channel_id
        status = "✅" if channel_id in channels else "❌"
        buttons.append([InlineKeyboardButton(text=f"{status} {title}", callback_data=f"channel_menu|{channel_id}")])

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_channels")])
    await callback.message.edit_text("🔍 Канали:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


class AddChannelState(StatesGroup):
    waiting_forward = State()


@router.callback_query(F.data == "add_channel")
async def ask_channel_to_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddChannelState.waiting_forward)
    await callback.message.edit_text("📥 Перешліть повідомлення з каналу або надішліть @username / ID / посилання на канал")

@router.message(AddChannelState.waiting_forward)
async def handle_text_add_channel(message: Message, state: FSMContext, bot: Bot):
    raw = message.text.strip() if message.text else ""
    input_data = None
    chat = None
    chat_dict = None

    if message.forward_from_chat:
        chat = message.forward_from_chat
        input_data = str(chat.id)
    elif raw.startswith("https://t.me/"):
        extracted = raw.split("https://t.me/")[-1].split("/")[0]
        input_data = extracted.lstrip("@")
    elif raw.startswith("@"):
        input_data = raw[1:]
    elif raw.startswith("-100") and raw[1:].isdigit():
        input_data = raw

    if not input_data:
        await message.answer("❌ Не вдалося розпізнати канал. Надішліть:\n• @username\n• посилання https://t.me/... \n• ID (-100...)\n• або переслане повідомлення з каналу")
        return

    try:
        # Спроба через bot API
        try:
            chat = await bot.get_chat(input_data)
            member = await bot.get_chat_member(chat.id, bot.id)
            chat_dict = {
                "id": chat.id,
                "username": f"@{chat.username}" if chat.username else None,
                "title": chat.title or f"ID {chat.id}"
            }
        except Exception as bot_exc:
            # Спроба через Telethon
            chat_dict = await resolve_channel_by_username(input_data)
            if not chat_dict:
                raise Exception(f"Telethon не зміг знайти @{input_data}")
            member = await bot.get_chat_member(chat_dict["id"], bot.id)

    except Exception as e:
        await message.answer(f"❌ Не вдалося отримати інформацію про канал. {e}")
        return

    if member.status not in ("administrator", "creator"):
        await message.answer("❌ Бот не є адміністратором цього каналу.")
        return

    channel_id = str(chat_dict["id"])
    entry = {
        "id": chat_dict["id"],
        "username": chat_dict.get("username"),
        "title": chat_dict.get("title") or channel_id
    }

    known = load_known_channels()
    channels = load_channels()

    known[channel_id] = entry
    channels[channel_id] = entry

    save_known_channels(known)
    save_channels(channels)

    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 До списку каналів", callback_data="view_channels")],
        [InlineKeyboardButton(text="🏠 Головне меню", callback_data="back_main")]
    ])
    await message.answer(f"✅ Канал <b>{entry['title']}</b> додано.", parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("channel_menu|"))
async def channel_menu(callback: CallbackQuery):
    channel_id = callback.data.split("|", 1)[1]
    channels = load_channels()
    known = load_known_channels()

    meta = channels.get(channel_id) or known.get(channel_id)
    if not meta:
        await callback.message.edit_text("❌ Канал не знайдено.")
        return

    title = meta.get("title") or meta.get("username") or channel_id

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Видалити канал", callback_data=f"delete_channel_confirm|{channel_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="view_channels")]
    ])
    await callback.message.edit_text(f"⚙️ Керування каналом:\n<b>{title}</b>", parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("delete_channel_confirm|"))
async def confirm_delete_channel(callback: CallbackQuery):
    channel_id = callback.data.split("|", 1)[1]
    known = load_known_channels()
    meta = known.get(channel_id)

    title = meta.get("title") or meta.get("username") or channel_id

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Так, видалити", callback_data=f"delete_channel_final|{channel_id}")],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="view_channels")]
    ])
    await callback.message.edit_text(f"⚠️ Ви впевнені, що хочете видалити канал <b>{title}</b>?", parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("delete_channel_final|"))
async def delete_channel_final(callback: CallbackQuery):
    channel_id = callback.data.split("|", 1)[1]

    channels = load_channels()
    known = load_known_channels()

    deleted = False
    if channel_id in channels:
        del channels[channel_id]
        save_channels(channels)
        deleted = True
    if channel_id in known:
        del known[channel_id]
        save_known_channels(known)
        deleted = True

    if deleted:
        await callback.message.edit_text("✅ Канал успішно видалено.")
    else:
        await callback.message.edit_text(f"⚠️ Канал <code>{channel_id}</code> не знайдено.", parse_mode="HTML")


@router.callback_query(F.data == "refresh_channels")
async def refresh_channels(callback: CallbackQuery, bot: Bot):
    known = load_known_channels()
    updated = {}

    for channel_id, meta in known.items():
        try:
            chat = await bot.get_chat(int(channel_id))
            member = await bot.get_chat_member(chat.id, bot.id)
            if member.status in ("administrator", "creator"):
                updated[channel_id] = {
                    "id": chat.id,
                    "username": f"@{chat.username}" if chat.username else None,
                    "title": chat.title or f"ID {chat.id}"
                }
        except Exception:
            continue

    save_channels(updated)

    count = len(updated)
    text = f"✅ Оновлено: знайдено {count} канал{'ів' if count != 1 else ''} з правами адміністратора."

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 До меню каналів", callback_data="menu_channels")],
        [InlineKeyboardButton(text="🏠 Головне меню", callback_data="back_main")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
