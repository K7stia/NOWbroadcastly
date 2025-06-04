from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def monitoring_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📂 Категорії моніторингу", callback_data="monitoring_categories")],
        [InlineKeyboardButton(text="🔍 Ручний моніторинг", callback_data="manual_monitoring")],
        [InlineKeyboardButton(text="🚀 Запустити сценарій", callback_data="scenario_menu")],
        [InlineKeyboardButton(text="⚙️ Модерація та моделі", callback_data="monitoring_config")],
        [InlineKeyboardButton(text="🧾 Журнал моніторингів", callback_data="monitoring_logs")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])

