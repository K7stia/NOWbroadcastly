import logging
import html
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from states.signature import SignatureState
from utils.json_storage import (
    load_channel_signature,
    save_channel_signature,
    delete_channel_signature,
    load_media,
    save_media
)

router = Router()

@router.callback_query(F.data.startswith("channel_menu|"))
async def channel_menu(callback: CallbackQuery):
    key = callback.data.split("|", 1)[1]
    media = load_media()
    channel_data = media.get(key)

    if not channel_data or channel_data.get("platform") != "telegram":
        await callback.message.edit_text("❌ Канал не знайдено або не є Telegram-каналом.")
        return

    channel_id = str(channel_data.get("id", key))
    display_name = channel_data.get("title", channel_id)

    info = load_channel_signature(channel_id)
    signature = info.get("signature")
    enabled = info.get("enabled", True)

    buttons = []
    if not signature:
        buttons.append([InlineKeyboardButton(text="➕ Додати підпис", callback_data=f"add_signature|{channel_id}")])
    else:
        toggle = "✅ Підпис додається" if enabled else "❌ Підпис не додається"
        buttons.append([InlineKeyboardButton(text=toggle, callback_data=f"toggle_signature|{channel_id}")])
        buttons.append([InlineKeyboardButton(text="✏️ Редагувати підпис", callback_data=f"edit_signature|{channel_id}")])
        buttons.append([InlineKeyboardButton(text="🗑 Видалити підпис", callback_data=f"delete_signature|{channel_id}")])

    buttons.append([InlineKeyboardButton(text="❌ Видалити канал", callback_data=f"confirm_delete_channel|{channel_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="view_media")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text(f"🔐 Налаштування для <b>{html.escape(display_name)}</b>:", reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("add_signature|"))
async def add_signature(callback: CallbackQuery, state: FSMContext):
    channel_id = callback.data.split("|", 1)[1]
    await state.set_state(SignatureState.waiting_signature)
    await state.update_data(channel_id=channel_id)
    await callback.message.edit_text(
        f"✍️ Введіть новий підпис для каналу ID <code>{channel_id}</code>:\n\n"
        "<b>Можна використовувати HTML-форматування:</b>\n"
        "• <code>&lt;b&gt;жирний&lt;/b&gt;</code>\n"
        "• <code>&lt;i&gt;курсив&lt;/i&gt;</code>\n"
        "• <code>&lt;a href='https://example.com'&gt;лінк&lt;/a&gt;</code>\n\n"
        "❗️Підпис буде доданий в кінці кожної публікації, якщо увімкнено",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("edit_signature|"))
async def edit_signature(callback: CallbackQuery, state: FSMContext):
    channel_id = callback.data.split("|", 1)[1]
    current = load_channel_signature(channel_id).get("signature", "(порожній)")
    await state.set_state(SignatureState.waiting_signature)
    await state.update_data(channel_id=channel_id)
    await callback.message.edit_text(
        f"✍️ Введіть новий підпис для каналу ID <code>{channel_id}</code>:\n\n"
        f"<b>Поточний підпис:</b>\n<code>{html.escape(current)}</code>\n\n"
        "<b>Можна використовувати HTML-форматування:</b>\n"
        "• <code>&lt;b&gt;жирний&lt;/b&gt;</code>\n"
        "• <code>&lt;i&gt;курсив&lt;/i&gt;</code>\n"
        "• <code>&lt;a href='https://example.com'&gt;лінк&lt;/a&gt;</code>\n\n"
        "❗️Підпис буде доданий в кінці кожної публікації, якщо увімкнено",
        parse_mode="HTML"
    )


@router.message(SignatureState.waiting_signature)
async def process_signature_input(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    channel_id = data.get("channel_id")
    save_channel_signature(channel_id, text)

    media = load_media()
    display_name = media.get(str(channel_id), {}).get("title", str(channel_id))

    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ До налаштувань каналу", callback_data=f"channel_menu|{channel_id}")],
        [InlineKeyboardButton(text="🏠 На головне меню", callback_data="back_main")]
    ])
    await message.answer(
        f"✅ Підпис для <b>{html.escape(display_name)}</b> збережено.\n\n"
        f"<i>Новий підпис:</i>\n<code>{html.escape(text)}</code>",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("toggle_signature|"))
async def toggle_signature(callback: CallbackQuery):
    channel_id = callback.data.split("|", 1)[1]
    info = load_channel_signature(channel_id)
    info["enabled"] = not info.get("enabled", True)
    save_channel_signature(channel_id, info.get("signature", ""), info["enabled"])
    await channel_menu(callback)


@router.callback_query(F.data.startswith("delete_signature|"))
async def delete_signature(callback: CallbackQuery):
    channel_id = callback.data.split("|", 1)[1]
    delete_channel_signature(channel_id)
    await channel_menu(callback)


@router.callback_query(F.data.startswith("confirm_delete_channel|"))
async def confirm_delete_channel(callback: CallbackQuery):
    channel_id = callback.data.split("|", 1)[1]
    media = load_media()
    display_name = media.get(str(channel_id), {}).get("title", channel_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗑 Так, видалити", callback_data=f"delete_channel|{channel_id}"),
            InlineKeyboardButton(text="◀️ Скасувати", callback_data=f"channel_menu|{channel_id}")
        ]
    ])
    await callback.message.edit_text(f"⚠️ Ви впевнені, що хочете видалити канал <b>{html.escape(display_name)}</b>?", reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("delete_channel|"))
async def delete_channel(callback: CallbackQuery):
    channel_id = callback.data.split("|", 1)[1]
    media = load_media()
    if channel_id in media:
        media.pop(channel_id)
        save_media(media)
        delete_channel_signature(channel_id)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📄 До списку медіа", callback_data="view_media")],
            [InlineKeyboardButton(text="🏠 На головне меню", callback_data="back_main")]
        ])
        await callback.message.edit_text(f"🗑 Канал ID <b>{channel_id}</b> видалено зі списку.", reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.edit_text(f"⚠️ Канал ID <b>{channel_id}</b> не знайдено у списку.", parse_mode="HTML")
