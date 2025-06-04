from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.json_storage import load_monitoring_groups, load_known_media

def scenario_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Створити сценарій", callback_data="create_scenario")],
        [InlineKeyboardButton(text="📋 Переглянути сценарії", callback_data="list_scenarios")],
        [InlineKeyboardButton(text="⚙️ Активація сценаріїв", callback_data="activate_scenarios")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])

def get_monitoring_group_keyboard(selected: list[str]) -> InlineKeyboardMarkup:
    groups = load_monitoring_groups()
    buttons = []
    for group in groups:
        mark = "✅" if group in selected else "◾️"
        buttons.append([InlineKeyboardButton(text=f"{mark} {group}", callback_data=f"toggle_group_sc|{group}")])
    buttons.append([InlineKeyboardButton(text="➡️ Підтвердити вибір", callback_data="confirm_groups_sc")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_target_media_keyboard(selected: list[str | int]) -> InlineKeyboardMarkup:
    selected_ids = {str(s) for s in selected}  # нормалізуємо до рядків для порівняння
    media = load_known_media()
    buttons = []

    for media_id, info in media.items():
        mark = "✅" if str(media_id) in selected_ids else "◾️"
        title = info.get("title") or media_id
        icon = {
            "telegram": "📢", "facebook": "📘", "instagram": "📸", "twitter": "🐦"
        }.get(info.get("platform", ""), "❔")
        buttons.append([InlineKeyboardButton(text=f"{mark} {icon} {title}", callback_data=f"toggle_media_sc|{media_id}")])

    buttons.append([InlineKeyboardButton(text="➡️ Підтвердити вибір", callback_data="confirm_targets_sc")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_scenario_options_keyboard(rewrite: bool, moderation: bool, skip: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✍️ Рерайт: {'✅' if rewrite else '❌'}", callback_data="toggle_option_sc|rewrite")],
        [InlineKeyboardButton(text=f"🛡 Модерація: {'✅' if moderation else '❌'}", callback_data="toggle_option_sc|moderation")],
        [InlineKeyboardButton(text=f"↪️ Пропускати репости: {'✅' if skip else '❌'}", callback_data="toggle_option_sc|skip_forwards")],
        [InlineKeyboardButton(text="➡️ Підтвердити", callback_data="confirm_options_sc")]
    ])

def get_schedule_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🕐 Точний час", callback_data="schedule_mode_sc|fixed_times")],
        [InlineKeyboardButton(text="🎲 Рандом в інтервалі", callback_data="schedule_mode_sc|random_in_intervals")],
        [InlineKeyboardButton(text="🔁 Постійно в інтервалі", callback_data="schedule_mode_sc|loop_in_intervals")]
    ])

def get_model_keyboard_for_scenarios():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Популярне", callback_data="scenario_model|popular")],
        [InlineKeyboardButton(text="🕒 Найновіше", callback_data="scenario_model|latest")],
        [InlineKeyboardButton(text="📈 Тренд", callback_data="scenario_model|trending")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="scenario_back_to_options")]
    ])
