from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def monitoring_target_kb(
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
            platform = info.get("platform", "unknown")
            title = info.get("title", channel)
            icon = PLATFORM_ICONS.get(platform, "❔")
            mark = "✅" if channel in selected_channels else "◾️"
            label = f"{mark} {icon} {title}"
            buttons.append([
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"manual_toggle_channel|{channel}"
                )
            ])

    if show_groups:
        for group in groups:
            mark = "✅" if group in selected_groups else "◾️"
            buttons.append([
                InlineKeyboardButton(
                    text=f"{mark} {group}",
                    callback_data=f"manual_toggle_group|{group}"
                )
            ])

    buttons.append([InlineKeyboardButton(text="➡️ Підтвердити вибір", callback_data="monitor_proceed_targets")])
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="manual_monitoring"),
        InlineKeyboardButton(text="🏠 Головне меню", callback_data="back_main")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def monitoring_mode_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Вибрати медіа (канали/сторінки)", callback_data="monitor_mode|channels")],
        [InlineKeyboardButton(text="🧩 Вибрати групу(и)", callback_data="monitor_mode|groups")],
        [InlineKeyboardButton(text="🔀 Мікс: медіа + групи", callback_data="monitor_mode|mix")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="manual_monitoring")]
    ])

def monitoring_options_kb(moderation: bool, rewrite: bool, skip_forwards: bool) -> InlineKeyboardMarkup:
    mod_label = "🛡 Модерація: ✅" if moderation else "🛡 Модерація: ❌"
    rew_label = "✍️ Рерайт: ✅" if rewrite else "✍️ Рерайт: ❌"
    skip_label = "↪️ Пропускати репости: ✅" if skip_forwards else "↪️ Пропускати репости: ❌"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=mod_label, callback_data="toggle_moderation")],
        [InlineKeyboardButton(text=rew_label, callback_data="toggle_rewrite")],
        [InlineKeyboardButton(text=skip_label, callback_data="toggle_skip_forwards")],
        [InlineKeyboardButton(text="🚀 Запустити моніторинг", callback_data="manual_monitor_launch")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="manual_monitoring")]
    ])
