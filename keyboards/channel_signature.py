from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def signature_menu_kb(signature_exists: bool) -> InlineKeyboardMarkup:
    buttons = []
    if signature_exists:
        buttons.append([InlineKeyboardButton(text="✏️ Змінити підпис", callback_data="change_signature")])
        buttons.append([InlineKeyboardButton(text="🗑 Видалити підпис", callback_data="delete_signature")])
    else:
        buttons.append([InlineKeyboardButton(text="➕ Встановити підпис", callback_data="change_signature")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

