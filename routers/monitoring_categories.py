import re
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from utils.json_storage import load_monitoring_groups, save_monitoring_groups, get_trim_settings, update_trim_settings
from states.monitoring_states import ManualMonitorState
from keyboards.monitoring_keyboards import get_channel_settings_keyboard
from telethon.tl.types import PeerChannel
from utils.telethon_client import client

router = Router()

class MonitorCategoryState(StatesGroup):
    waiting_name = State()
    waiting_channel = State()
    current_category = State()

def category_created_kb(category_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Додати канали", callback_data=f"add_cat_channel|{category_name}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="monitoring_categories")],
        [InlineKeyboardButton(text="🏠 Головне меню", callback_data="back_main")]
    ])

def channel_added_kb(category_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Додати ще канал", callback_data=f"add_cat_channel|{category_name}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"edit_category|{category_name}")],
        [InlineKeyboardButton(text="🏠 Головне меню", callback_data="back_main")]
    ])

@router.callback_query(F.data == "monitoring_categories")
async def monitoring_categories_menu(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗂 Переглянути / редагувати", callback_data="view_monitoring_categories")],
        [InlineKeyboardButton(text="➕ Створити категорію", callback_data="create_monitoring_category")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="monitoring_menu")]
    ])
    await callback.message.edit_text("📂 Категорії моніторингу:", reply_markup=kb)



@router.callback_query(F.data == "create_monitoring_category")
async def ask_category_name(callback: CallbackQuery, state: FSMContext):
    await state.set_state(MonitorCategoryState.waiting_name)
    await callback.message.edit_text(
        "📝 Введіть назву нової категорії моніторингу:\n\n"
        "✅ Дозволені символи:\n"
        "– латинські літери (A–Z, a–z)\n"
        "– цифри (0–9)\n"
        "– пробіли\n"
        "– спецсимволи: <code>|</code>, <code>_</code>, <code>:</code>\n\n"
        "❌ Заборонено використовувати крапки (.), слеші (/), лапки та інші символи.",
        parse_mode="HTML"
    )

@router.message(MonitorCategoryState.waiting_name)
async def process_category_name(message: Message, state: FSMContext):
    import re
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    name_raw = message.text.strip()

    # Дозволені символи: укр/лат букви, цифри, пробіли, | _ : -
    allowed_pattern = r"^[a-zA-Zа-яА-ЯіїєґІЇЄҐ0-9 |_:.-]+$"

    if not re.fullmatch(allowed_pattern, name_raw):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Спробувати ще раз", callback_data="create_monitoring_category")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="monitoring_categories")]
        ])
        await message.answer(
            "❗️Недопустимі символи в назві.\n\n"
            "✅ Дозволено:\n"
            "– літери (латиниця / українська)\n"
            "– цифри\n"
            "– пробіли\n"
            "– спецсимволи: <code>|</code>, <code>_</code>, <code>:</code>, <code>-</code>",
            reply_markup=kb,
            parse_mode="HTML"
        )
        return

    # Заміна пробілів на підкреслення
    name = name_raw.replace(" ", "_")

    data = load_monitoring_groups()
    if name in data:
        await message.answer("❗️ Категорія з такою назвою вже існує.")
    else:
        data[name] = {"channels": [], "skip_seen": True}
        save_monitoring_groups(data)
        await message.answer(
            f"✅ Категорія <b>{name}</b> створена.",
            reply_markup=category_created_kb(name),
            parse_mode="HTML"
        )
    await state.clear()

@router.callback_query(F.data == "view_monitoring_categories")
async def list_categories(callback: CallbackQuery):
    data = load_monitoring_groups()
    if not data:
        await callback.message.edit_text("ℹ️ Ще не створено жодної категорії.")
        return

    buttons = [
        [InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"edit_category|{cat}")]
        for cat in sorted(data.keys())
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="monitoring_categories")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("🗂 Виберіть категорію:", reply_markup=kb)

@router.callback_query(F.data.startswith("edit_category|"))
async def edit_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("|", 1)[1]
    data = load_monitoring_groups()
    category_data = data.get(category, {})
    skip_seen = category_data.get("skip_seen", True)
    channels = category_data.get("channels", [])

    lines = [f"📂 <b>{category}</b>", f"Каналів: <b>{len(channels)}</b>",
             f"🛑 Пропускати вже оброблені: {'✅' if skip_seen else '❌'}"]
    text = "\n".join(lines)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список каналів", callback_data=f"list_cat_channels|{category}")],
        [InlineKeyboardButton(text="➕ Додати канал", callback_data=f"add_cat_channel|{category}")],
        [InlineKeyboardButton(text="🔁 Перемкнути skip_seen", callback_data=f"toggle_skip_seen|{category}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="view_monitoring_categories")]
    ])
    await state.update_data(current_category=category)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("toggle_skip_seen|"))
async def toggle_skip_seen(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("|", 1)[1]
    data = load_monitoring_groups()
    if category in data:
        data[category]["skip_seen"] = not data[category].get("skip_seen", True)
        save_monitoring_groups(data)
    await edit_category(callback, state)

@router.callback_query(F.data.startswith("add_cat_channel|"))
async def ask_channel_to_add(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("|", 1)[1]
    await state.set_state(MonitorCategoryState.waiting_channel)
    await state.update_data(current_category=category)
    await callback.message.edit_text("📥 Перешліть повідомлення з каналу або надішліть @username / ID каналу:")

@router.message(MonitorCategoryState.waiting_channel)
async def process_channel_addition(message: Message, state: FSMContext, bot: Bot):
    import logging

    data = await state.get_data()
    category = data.get("current_category")
    raw = message.text.strip() if message.text else ""

    input_data = None
    if message.forward_from_chat:
        input_data = message.forward_from_chat.id
    elif raw.startswith("https://t.me/"):
        input_data = "@" + raw.split("https://t.me/")[-1].split("/")[0]
    elif raw.startswith("@") or raw.startswith("-100") or raw.isdigit():
        input_data = raw

    if not input_data:
        await message.answer("❌ Не вдалося розпізнати канал. Надішліть @username, ID або переслане повідомлення.")
        return

    chat = None
    try:
        chat = await bot.get_chat(input_data)
        title = chat.title
        cid = chat.id
        username = chat.username
        logging.debug(f"✅ Отримано через Bot API: {title}")
    except Exception as bot_error:
        logging.warning(f"⚠️ Bot API не вдалося: {bot_error}")
        try:
            await client.start()
            if str(input_data).startswith("-100"):
                peer = PeerChannel(int(str(input_data)[4:]))
            elif str(input_data).isdigit():
                peer = PeerChannel(int(input_data))
            else:
                peer = input_data  # username

            entity = await client.get_entity(peer)
            cid = int(f"-100{entity.id}") if entity.id > 0 else entity.id
            title = getattr(entity, "title", f"ID {cid}")
            username = getattr(entity, "username", None)
            logging.debug(f"✅ Отримано через Telethon: {title}")
        except Exception as telethon_error:
            logging.error(f"❌ Не вдалося через Telethon: {telethon_error}")
            await message.answer(f"❌ Не вдалося отримати інформацію про канал. {telethon_error}")
            return
        finally:
            await client.disconnect()

    groups = load_monitoring_groups()
    if category not in groups:
        await message.answer("❗️ Категорію не знайдено.")
        return

    new_entry = {
        "id": cid,
        "username": f"@{username}" if username else str(cid),
        "title": title,
        "lines_to_trim": 0,
        "trim_phrases": []
    }
    groups[category]["channels"].append(new_entry)
    save_monitoring_groups(groups)

    await message.answer(
        f"✅ Канал <b>{title}</b> додано до категорії <b>{category}</b>.",
        reply_markup=channel_added_kb(category),
        parse_mode="HTML"
    )
    await state.clear()


@router.callback_query(F.data.startswith("list_cat_channels|"))
async def list_cat_channels(callback: CallbackQuery):
    category = callback.data.split("|", 1)[1]
    groups = load_monitoring_groups()
    channels = groups.get(category, {}).get("channels", [])

    if not channels:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ До списку категорій", callback_data="view_monitoring_categories")],
            [InlineKeyboardButton(text="🏠 На головну", callback_data="back_main")]
        ])
        await callback.message.edit_text(
            f"✅ Канал видалено з категорії <b>{category}</b>.",
            reply_markup=kb,
            parse_mode="HTML"
        )
        return

    buttons = [
        [InlineKeyboardButton(text=f"⚙️ {c['title']}", callback_data=f"channel_settings|{category}|{c['id']}")]
        for c in channels
    ]
    buttons.append([InlineKeyboardButton(text="◀️ До списку категорій", callback_data="view_monitoring_categories")])
    buttons.append([InlineKeyboardButton(text="🏠 На головну", callback_data="back_main")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(
        f"📋 Канали в категорії <b>{category}</b>:",
        reply_markup=kb,
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("remove_cat_channel|"))
async def remove_cat_channel(callback: CallbackQuery):
    _, category, cid = callback.data.split("|")
    groups = load_monitoring_groups()
    if category in groups:
        groups[category]["channels"] = [c for c in groups[category]["channels"] if str(c["id"]) != cid]
        save_monitoring_groups(groups)
    await list_cat_channels(callback)


@router.callback_query(F.data.startswith("confirm_remove_channel|"))
async def confirm_remove_channel(callback: CallbackQuery):
    _, category, cid = callback.data.split("|")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Так, видалити", callback_data=f"remove_cat_channel|{category}|{cid}"),
            InlineKeyboardButton(text="◀️ Скасувати", callback_data=f"list_cat_channels|{category}")
        ]
    ])
    await callback.message.edit_text(
        f"❗️ Ви впевнені, що хочете видалити цей канал з категорії <b>{category}</b>?",
        reply_markup=kb,
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("channel_settings|"))
async def channel_settings(callback: CallbackQuery):

    _, category, cid = callback.data.split("|")
    channel_id = int(cid)
    settings = get_trim_settings(category, channel_id)

    # Завантаження повної інформації про канал
    groups = load_monitoring_groups()
    channels = groups.get(category, {}).get("channels", [])
    ch = next((c for c in channels if c.get("id") == channel_id), None)

    title_or_id = (
        ch.get("title") if ch and ch.get("title") else
        ch.get("username") if ch and ch.get("username") else
        f"{channel_id}"
    )

    # Підпис джерела
    sig_data = ch.get("source_signature", {}) if ch else {}
    sig_text = sig_data.get("text", "").strip() if sig_data.get("enabled") else "— (вимкнено або не задано)"

    text = (
        f"⚙️ Налаштування каналу <b>{title_or_id}</b> у категорії <b>{category}</b>:\n\n"
        f"🖋 <b>Підпис джерела</b>: {sig_text or '—'}\n"
        f"✂️ <b>Кількість рядків для обрізки</b>: <code>{settings['lines_to_trim']}</code>\n"
        f"🧹 <b>Ключові фрази</b>: {', '.join(settings['trim_phrases']) or '—'}"
    )

    kb = get_channel_settings_keyboard(category, channel_id)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("change_lines|"))
async def change_lines(callback: CallbackQuery, state: FSMContext):
    _, category, cid = callback.data.split("|")
    await state.set_state(ManualMonitorState.editing_trim_lines)
    await state.update_data(category=category, channel_id=int(cid))
    await callback.message.edit_text("✂️ Введіть кількість рядків, які потрібно обрізати з кінця тексту:")

@router.message(ManualMonitorState.editing_trim_lines)
async def process_trim_lines(message: Message, state: FSMContext):
    try:
        count = int(message.text.strip())
        if count < 0 or count > 20:
            raise ValueError("недопустиме число")
    except:
        await message.answer("❗️Введіть число від 0 до 20.")
        return

    data = await state.get_data()
    category = data["category"]
    channel_id = data["channel_id"]

    update_trim_settings(category, channel_id, lines_to_trim=count)
    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ До каналів категорії", callback_data=f"list_cat_channels|{category}")],
        [InlineKeyboardButton(text="🏠 На головну", callback_data="back_main")]
    ])

    await message.answer(
        "✅ Кількість рядків оновлено.",
        reply_markup=kb
    )


@router.callback_query(F.data.startswith("change_phrases|"))
async def change_phrases(callback: CallbackQuery, state: FSMContext):
    _, category, cid = callback.data.split("|")
    await state.set_state(ManualMonitorState.editing_trim_phrases)
    await state.update_data(category=category, channel_id=int(cid))
    await callback.message.edit_text(
        "🧹 Введіть фрази для пошуку (розділяйте комами):\n\n"
        "<i>Наприклад:</i>\n<code>Підписатись, наш канал, читайте більше</code>",
        parse_mode="HTML"
    )

@router.message(ManualMonitorState.editing_trim_phrases)
async def process_trim_phrases(message: Message, state: FSMContext):
    phrases = [p.strip() for p in message.text.split(",") if p.strip()]
    data = await state.get_data()
    category = data["category"]
    channel_id = data["channel_id"]

    update_trim_settings(category, channel_id, trim_phrases=phrases)
    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ До каналів категорії", callback_data=f"list_cat_channels|{category}")],
        [InlineKeyboardButton(text="🏠 На головну", callback_data="back_main")]
    ])

    await message.answer("✅ Фрази для обрізання оновлено.", reply_markup=kb)
