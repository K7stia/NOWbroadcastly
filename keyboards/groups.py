from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.json_storage import load_known_media, load_groups

def group_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📃 Переглянути групи", callback_data="list_groups")],
        [InlineKeyboardButton(text="➕ Додати групу", callback_data="add_group")],
        [InlineKeyboardButton(text="➖ Видалити групу", callback_data="delete_group")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])

def delete_group_kb(group_names: list[str]) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text=name, callback_data=f"delete_{i}")] for i, name in enumerate(group_names)]
    buttons.append([InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_delete")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def channels_group_kb(group_name: str, mode: str = "selected") -> InlineKeyboardMarkup:
    all_media = load_known_media()  # {id_str: {id: ..., title: ..., platform: ...}}
    groups = load_groups()
    group_channels = groups.get(group_name, [])  # [{id: ..., title: ..., platform: ...}, ...]

    selected_ids = {str(c["id"]) for c in group_channels if isinstance(c, dict)}
    buttons = []

    for id_str, info in sorted(all_media.items(), key=lambda x: x[1].get("title") or x[0]):
        platform = info.get("platform", "telegram")
        display_title = f"[{platform}] {info.get('title') or id_str}"
        is_selected = id_str in selected_ids
        icon = "✅" if is_selected else "➖"

        if mode == "selected" and not is_selected:
            continue

        buttons.append([
            InlineKeyboardButton(
                text=f"{icon} {display_title}",
                callback_data=f"toggle_group_channel|{id_str}|{group_name}"
            )
        ])

    control_buttons = []
    if mode == "selected":
        control_buttons.append(
            [InlineKeyboardButton(text="➕ Додати ще медіа", callback_data=f"show_all_channels|{group_name}")]
        )

    control_buttons.extend([
        [InlineKeyboardButton(text="✏️ Переіменувати групу", callback_data=f"rename_group|{group_name}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_groups")]
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons + control_buttons)
