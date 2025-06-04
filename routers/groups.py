import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from utils.json_storage import load_groups, save_groups, load_known_media
from states.group import AddGroup, RenameGroup
from keyboards.groups import group_menu_kb, channels_group_kb
from states.monitoring_states import SourceSignatureState, StopWordsState
from keyboards.monitoring_keyboards import get_source_signature_keyboard, get_stop_words_keyboard
from utils.json_storage import update_source_signature, load_monitoring_groups, save_monitoring_groups, delete_source_signature, get_stop_words, update_stop_words, delete_stop_words

router = Router()

@router.callback_query(F.data == "menu_groups")
async def cb_manage_groups(callback: CallbackQuery):
    await callback.message.edit_text("Керування групами медіа:", reply_markup=group_menu_kb())


@router.callback_query(F.data == "add_group")
async def cb_add_group(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddGroup.waiting_name)
    await callback.message.edit_text("Введіть назву нової групи медіа:")


@router.message(AddGroup.waiting_name)
async def add_group_name(message: Message, state: FSMContext):
    group_name = message.text.strip()
    if not group_name:
        await message.answer("❗️ Назва не може бути порожньою. Введіть іншу назву або /cancel.")
        return
    groups = load_groups()
    if group_name in groups:
        await message.answer("❗️ Група з такою назвою вже існує.")
        return
    groups[group_name] = []
    save_groups(groups)
    await state.clear()
    await show_group_edit_menu(message, group_name, mode="selected")


@router.callback_query(F.data.startswith("edit_group|"))
async def cb_edit_group(callback: CallbackQuery):
    group_name = callback.data.split("|", 1)[1]
    await show_group_edit_menu(callback.message, group_name, mode="selected")


@router.callback_query(F.data.startswith("show_all_channels|"))
async def cb_show_all_channels(callback: CallbackQuery):
    group_name = callback.data.split("|", 1)[1]
    await show_group_edit_menu(callback.message, group_name, mode="all")


async def show_group_edit_menu(target, group_name: str, mode: str = "selected"):
    text = (
        f"<b>Група:</b> <u>{group_name}</u>\n"
        "Тут ви можете редагувати список медіа (Telegram/FB), які входять у цю групу,\n"
        "а також перейменувати її."
    )
    markup = channels_group_kb(group_name, mode=mode)

    if isinstance(target, Message):
        await target.answer(text, reply_markup=markup, parse_mode="HTML")
    elif isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=markup, parse_mode="HTML")


@router.callback_query(F.data.startswith("toggle_group_channel|"))
async def toggle_group_channel(callback: CallbackQuery):
    _, media_id, group_name = callback.data.split("|")
    groups = load_groups()
    group = groups.get(group_name, [])
    known_media = load_known_media()
    media_info = known_media.get(media_id)

    if not media_info:
        await callback.answer("❗️ Медіа не знайдено в системі.", show_alert=True)
        return

    existing_ids = {str(c["id"]) for c in group if isinstance(c, dict)}
    if str(media_info["id"]) in existing_ids:
        group = [c for c in group if str(c.get("id")) != str(media_info["id"])]
    else:
        group.append({
            "id": media_info["id"],
            "title": media_info.get("title"),
            "platform": media_info.get("platform", "telegram")
        })

    groups[group_name] = group
    save_groups(groups)

    # 🔁 Оновлюємо клавіатуру після натискання
    new_markup = channels_group_kb(group_name, mode="all")
    await callback.message.edit_reply_markup(reply_markup=new_markup)
    await callback.answer("Оновлено")


@router.callback_query(F.data.startswith("rename_group|"))
async def cb_rename_group(callback: CallbackQuery, state: FSMContext):
    group_name = callback.data.split("|", 1)[1]
    await state.set_state(RenameGroup.waiting_new_name)
    await state.update_data(old_name=group_name)
    await callback.message.edit_text(f"✏️ Введіть нову назву для групи \"{group_name}\":")


@router.message(RenameGroup.waiting_new_name)
async def process_group_rename(message: Message, state: FSMContext):
    new_name = message.text.strip()
    data = await state.get_data()
    old_name = data.get("old_name")

    if not new_name or new_name == old_name:
        await message.answer("⚠️ Назва не змінена. Введіть нову назву або /cancel.")
        return

    groups = load_groups()
    if new_name in groups:
        await message.answer("❗️ Група з такою назвою вже існує. Введіть іншу.")
        return

    channels = groups.pop(old_name, [])
    groups[new_name] = channels
    save_groups(groups)
    await state.clear()
    await message.answer(f"✅ Групу перейменовано в \"{new_name}\".")
    await show_group_edit_menu(message, new_name, mode="selected")


@router.callback_query(F.data == "list_groups")
async def cb_list_groups(callback: CallbackQuery):
    groups = load_groups()
    if not groups:
        await callback.message.edit_text("ℹ️ Ще не створено жодної групи.")
        return

    buttons = [
        [InlineKeyboardButton(text=f"🔧 {name}", callback_data=f"edit_group|{name}")]
        for name in sorted(groups.keys())
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_groups")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("📃 Список груп:", reply_markup=kb)


@router.callback_query(F.data == "delete_group")
async def cb_delete_group(callback: CallbackQuery):
    groups = load_groups()
    if not groups:
        await callback.answer("ℹ️ Немає жодної групи для видалення.", show_alert=True)
        return

    buttons = [
        [InlineKeyboardButton(text=f"🗑 {name}", callback_data=f"delete_group_confirm|{name}")]
        for name in sorted(groups.keys())
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_groups")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("❌ Оберіть групу для видалення:", reply_markup=kb)


@router.callback_query(F.data.startswith("delete_group_confirm|"))
async def cb_delete_group_confirm(callback: CallbackQuery):
    group_name = callback.data.split("|", 1)[1]
    groups = load_groups()
    if group_name in groups:
        del groups[group_name]
        save_groups(groups)
    await callback.message.edit_text(f"✅ Групу <b>{group_name}</b> видалено.", parse_mode="HTML")
    await cb_manage_groups(callback)

@router.callback_query(F.data.startswith("edit_source_signature|"))
async def show_source_signature_menu(callback: CallbackQuery):
    category, channel_id = callback.data.split("|")[1:]
    channel_id = int(channel_id)

    groups = load_monitoring_groups()
    sig_data = None
    for ch in groups.get(category, {}).get("channels", []):
        if ch.get("id") == channel_id:
            sig_data = ch.get("source_signature", {})
            break

    text = sig_data.get("text", "") if sig_data else ""
    enabled = sig_data.get("enabled", True) if sig_data else False

    await callback.message.edit_text(
        f"🖋 Поточний підпис джерела:\n\n{text or '— немає —'}",
        reply_markup=get_source_signature_keyboard(category, channel_id, text, enabled)
    )

@router.callback_query(F.data.startswith("edit_source_signature_text|"))
async def prompt_source_signature_edit(callback: CallbackQuery, state: FSMContext):
    category, channel_id = callback.data.split("|")[1:]
    channel_id = int(channel_id)

    # Завантажити назву каналу
    title = "обраного каналу"
    groups = load_monitoring_groups()
    for ch in groups.get(category, {}).get("channels", []):
        if ch.get("id") == channel_id:
            title = ch.get("title") or ch.get("username") or str(channel_id)
            break

    await state.update_data(category=category, channel_id=channel_id)
    await state.set_state(SourceSignatureState.editing)
    await callback.message.edit_text(f"✏️ Введіть новий текст підпису джерела для <b>{title}</b>:", parse_mode="HTML")

@router.message(SourceSignatureState.editing)
async def save_source_signature_text(message, state: FSMContext):

    data = await state.get_data()
    category = data["category"]
    channel_id = data["channel_id"]
    text = message.text.strip()

    update_source_signature(category, channel_id, text=text, enabled=True)

    # Отримуємо назву каналу
    groups = load_monitoring_groups()
    title = next(
        (ch.get("title") or ch.get("username") or str(channel_id)
         for ch in groups.get(category, {}).get("channels", [])
         if ch.get("id") == channel_id),
        str(channel_id)
    )

    await message.answer(
        f"✅ Підпис джерела для <b>{title}</b> оновлено.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад до каналу", callback_data=f"edit_source_signature|{category}|{channel_id}")],
            [InlineKeyboardButton(text="🏠 На головну", callback_data="back_main")]
        ])
    )
    await state.clear()


@router.callback_query(F.data.startswith("toggle_source_signature|"))
async def toggle_source_signature(callback: CallbackQuery):
    category, channel_id = callback.data.split("|")[1:]
    channel_id = int(channel_id)

    groups = load_monitoring_groups()
    for ch in groups.get(category, {}).get("channels", []):
        if ch.get("id") == channel_id:
            current = ch.get("source_signature", {"enabled": False, "text": ""})
            current["enabled"] = not current.get("enabled", False)
            ch["source_signature"] = current
            break

    save_monitoring_groups(groups)
    await show_source_signature_menu(callback)

@router.callback_query(F.data.startswith("delete_source_signature|"))
async def delete_source_signature(callback: CallbackQuery):

    category, channel_id = callback.data.split("|")[1:]
    channel_id = int(channel_id)

    delete_source_signature(category, channel_id)

    # Отримуємо назву каналу
    groups = load_monitoring_groups()
    title = next(
        (ch.get("title") or ch.get("username") or str(channel_id)
         for ch in groups.get(category, {}).get("channels", [])
         if ch.get("id") == channel_id),
        str(channel_id)
    )

    await callback.message.edit_text(
        f"🗑 Підпис джерела для <b>{title}</b> видалено.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад до каналу", callback_data=f"edit_source_signature|{category}|{channel_id}")],
            [InlineKeyboardButton(text="🏠 На головну", callback_data="back_main")]
        ])
    )

@router.callback_query(F.data.startswith("edit_stop_words|"))
async def show_stop_words_menu(callback: CallbackQuery):
    category, channel_id = callback.data.split("|", 2)[1:]
    channel_id = int(channel_id)
    current = get_stop_words(category, channel_id)
    await callback.message.edit_text(
        f"🧾 <b>Стоп-слова для каналу</b>:\n\n{chr(10).join(f'– {w}' for w in current) or '— немає —'}",
        parse_mode="HTML",
        reply_markup=get_stop_words_keyboard(category, channel_id, current)
    )

@router.callback_query(F.data.startswith("add_stop_word|"))
async def start_add_stop_word(callback: CallbackQuery, state: FSMContext):
    category, channel_id = callback.data.split("|", 2)[1:]
    await state.update_data(category=category, channel_id=int(channel_id))
    await state.set_state(StopWordsState.adding)
    await callback.message.edit_text("✏️ Введіть нове стоп-слово:")

@router.message(StopWordsState.adding)
async def save_new_stop_word(message: Message, state: FSMContext):
    data = await state.get_data()
    words = get_stop_words(data["category"], data["channel_id"])
    new_word = message.text.strip().lower()
    if new_word and new_word not in words:
        words.append(new_word)
        update_stop_words(data["category"], data["channel_id"], words)
    await state.clear()

    await message.answer(
        "✅ Стоп-слово додано.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"edit_stop_words|{data['category']}|{data['channel_id']}")],
            [InlineKeyboardButton(text="🏠 У головне меню", callback_data="back_main")]
        ])
    )

@router.callback_query(F.data.startswith("edit_stop_words_text|"))
async def prompt_edit_stop_words(callback: CallbackQuery, state: FSMContext):
    category, channel_id = callback.data.split("|", 2)[1:]
    channel_id = int(channel_id)
    current = get_stop_words(category, channel_id)
    await state.update_data(category=category, channel_id=channel_id)
    await state.set_state(StopWordsState.editing)
    await callback.message.edit_text(
        f"📝 Введіть новий список стоп-слів через кому:\n\n{', '.join(current)}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 У головне меню", callback_data="back_main")]
        ])
    )

@router.message(StopWordsState.editing)
async def save_stop_words_list(message: Message, state: FSMContext):
    data = await state.get_data()
    words = [w.strip().lower() for w in message.text.split(",") if w.strip()]
    update_stop_words(data["category"], data["channel_id"], words)
    await state.clear()

    await message.answer(
        "✅ Список стоп-слів оновлено.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"edit_stop_words|{data['category']}|{data['channel_id']}")],
            [InlineKeyboardButton(text="🏠 У головне меню", callback_data="back_main")]
        ])
    )

@router.callback_query(F.data.startswith("delete_stop_words|"))
async def clear_stop_words(callback: CallbackQuery):
    category, channel_id = callback.data.split("|", 2)[1:]
    channel_id = int(channel_id)
    delete_stop_words(category, channel_id)

    await callback.message.edit_text(
        "🗑 Список стоп-слів очищено.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"edit_stop_words|{category}|{channel_id}")],
            [InlineKeyboardButton(text="🏠 У головне меню", callback_data="back_main")]
        ])
    )
