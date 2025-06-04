from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.json_storage import load_config

async def send_post_to_moderation(bot: Bot, post: dict, output_channel: str, category: str, model: str):
    config = load_config()
    group_id = config.get("moderation_group_id")
    if not group_id:
        return

    text = post.get("text", "[без тексту]")[:1000]
    caption = (
        f"📥 <b>Новина для модерації</b>\n\n"
        f"<b>Категорія:</b> {category}\n"
        f"<b>Модель:</b> {model}\n"
        f"<b>Куди публікувати:</b> {output_channel}\n"
    )

    buttons = [
        [
            InlineKeyboardButton(text="✅ Опублікувати", callback_data=f"approve_post"),
            InlineKeyboardButton(text="⚙️ Налаштування", callback_data=f"moderation_options"),
        ]
    ]

    await bot.send_message(
        chat_id=group_id,
        text=caption + "\n\n" + text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
