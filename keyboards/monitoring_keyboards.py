from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.json_storage import load_monitoring_groups

def get_category_keyboard():
    groups = load_monitoring_groups()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=f"manual_select_category|{name}")]
            for name in sorted(groups.keys())
        ] + [[InlineKeyboardButton(text="◀️ Назад", callback_data="monitoring_menu")]]
    )

def get_model_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Популярне", callback_data="manual_model|popular")],
        [InlineKeyboardButton(text="🕒 Найновіше", callback_data="manual_model|latest")],
        [InlineKeyboardButton(text="📈 Тренд", callback_data="manual_model|trending")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="manual_monitoring")]
    ])

def get_channel_settings_keyboard(category: str, channel_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖋 Підпис джерела", callback_data=f"edit_source_signature|{category}|{channel_id}")],
        [InlineKeyboardButton(text="✂️ Змінити кількість рядків [обрізання]", callback_data=f"change_lines|{category}|{channel_id}")],
        [InlineKeyboardButton(text="🧹 Змінити фрази [обрізання]", callback_data=f"change_phrases|{category}|{channel_id}")],
        [InlineKeyboardButton(text="🚫 Стоп-слова", callback_data=f"edit_stop_words|{category}|{channel_id}")],
        [InlineKeyboardButton(text="🗑 Видалити канал", callback_data=f"confirm_remove_channel|{category}|{channel_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"list_cat_channels|{category}")]
    ])

def get_source_signature_keyboard(category: str, channel_id: int, current_text: str = "", enabled: bool = True) -> InlineKeyboardMarkup:
    toggle_label = "✅ Підпис додається" if enabled else "🚫 Підпис НЕ додається"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редагувати підпис", callback_data=f"edit_source_signature_text|{category}|{channel_id}")],
        [InlineKeyboardButton(text=toggle_label, callback_data=f"toggle_source_signature|{category}|{channel_id}")],
        [InlineKeyboardButton(text="🗑 Видалити підпис", callback_data=f"delete_source_signature|{category}|{channel_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"list_cat_channels|{category}")]
    ])

def get_stop_words_keyboard(category: str, channel_id: int, current: list[str]) -> InlineKeyboardMarkup:
    words_list = "\n".join(f"– {w}" for w in current) or "— немає —"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Додати слово", callback_data=f"add_stop_word|{category}|{channel_id}")],
        [InlineKeyboardButton(text="✏️ Редагувати всі", callback_data=f"edit_stop_words_text|{category}|{channel_id}")],
        [InlineKeyboardButton(text="🗑 Очистити", callback_data=f"delete_stop_words|{category}|{channel_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"list_cat_channels|{category}")]
    ])

