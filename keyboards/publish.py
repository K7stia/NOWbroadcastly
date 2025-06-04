from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def publish_mode_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Вибрати медіа (канали/сторінки)", callback_data="select_mode|channels")],
        [InlineKeyboardButton(text="🧩 Вибрати групу(и)", callback_data="select_mode|groups")],
        [InlineKeyboardButton(text="🔀 Мікс: канали + групи", callback_data="select_mode|mix")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ])

def publish_options_kb(sound_on: bool, use_signature: bool) -> InlineKeyboardMarkup:
    sound_label = "🔔 Звук: увімкнено" if sound_on else "🔕 Звук: вимкнено"
    sig_label = "✍ Підпис: увімкнено" if use_signature else "✍ Підпис: вимкнено"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=sound_label, callback_data="toggle_sound"),
            InlineKeyboardButton(text=sig_label, callback_data="toggle_signature")
        ],
        [InlineKeyboardButton(text="🚀 Опублікувати", callback_data="publish_now")],
        [InlineKeyboardButton(text="⏰ Запланувати", callback_data="schedule")]
    ])

def publish_target_kb(
    groups: dict[str, list],
    channels: dict[str, dict],
    selected_groups: list[str] = None,
    selected_channels: list[str] = None,
    show_channels: bool = True,
    show_groups: bool = True
) -> InlineKeyboardMarkup:
    selected_groups = selected_groups or []
    selected_channels = selected_channels or []

    PLATFORM_ICONS = {
        "telegram": "📢",
        "facebook": "📘",
        "instagram": "📸",
        "twitter": "🐦"
    }

    buttons = []

    if show_channels:
        for channel, info in channels.items():
            mark = "✅" if channel in selected_channels else "◾️"
            platform = info.get("platform", "unknown")
            icon = PLATFORM_ICONS.get(platform, "❔")
            title = info.get("title", channel)
            label = f"{mark} {icon} {title}"
            buttons.append([
                InlineKeyboardButton(text=label, callback_data=f"toggle_channel|{channel}")
            ])

    if show_groups:
        for group in groups:
            mark = "✅" if group in selected_groups else "◾️"
            buttons.append([
                InlineKeyboardButton(text=f"{mark} {group}", callback_data=f"toggle_group|{group}")
            ])

    buttons.append([InlineKeyboardButton(text="➡️ Далі", callback_data="proceed_to_content")])
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="publish_news"),
        InlineKeyboardButton(text="🏠 Головне меню", callback_data="back_main")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
