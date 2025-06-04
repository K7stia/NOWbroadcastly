import os
import openai
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils.json_storage import load_monitoring_groups, load_config, load_scenarios
from utils.telethon_fetcher import fetch_posts_for_category
from monitoring_moderation import send_post_to_moderation

router = Router()

openai.api_key = os.getenv("OPENAI_API_KEY")

async def rewrite_text(text: str, style: str) -> str:
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"Перефразуй цей текст у стилі: {style}"},
                {"role": "user", "content": text}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[❗️Помилка рерайту: {e}]\n{text}"

# 🚀 Основна функція запуску сценарію моніторингу
async def run_monitoring_scenario(bot: Bot, scenario_name: str):
    scenarios = load_scenarios()
    config = load_config()
    style = config.get("rewrite_style", "Перефразуй цей текст для Telegram-каналу")

    scenario = scenarios.get(scenario_name)
    if not scenario:
        print(f"❌ Сценарій '{scenario_name}' не знайдено.")
        return

    category = scenario.get("category")
    model = scenario.get("model")
    output_channel = scenario.get("output_channel")
    moderation = scenario.get("moderation", True)
    rewrite = scenario.get("rewrite", False)

    groups = load_monitoring_groups()
    channels = groups.get(category, {}).get("channels", [])
    posts = await fetch_posts_for_category(channels)

    if not posts:
        print(f"❌ Немає публікацій для категорії '{category}'")
        return

    top = posts[0]

    if rewrite:
        top["text"] = await rewrite_text(top["text"], style)

    if moderation:
        await send_post_to_moderation(bot, top, output_channel, category, model)
        print(f"📨 Пост надіслано на модерацію для '{output_channel}'")
        return

    try:
        await bot.send_message(chat_id=output_channel, text=top["text"], parse_mode="HTML")
        print(f"✅ Пост опубліковано у {output_channel}")
    except Exception as e:
        print(f"❗️ Не вдалося опублікувати пост: {e}")

# 📋 Команда для відображення списку сценаріїв і запуску вручну
@router.callback_query(F.data == "run_scenario")
async def show_scenarios(callback: CallbackQuery):
    scenarios = load_scenarios()
    if not scenarios:
        await callback.message.edit_text("❗️ Немає створених сценаріїв.")
        return

    buttons = [
        [InlineKeyboardButton(text=f"▶️ {name}", callback_data=f"launch_scenario|{name}")]
        for name in sorted(scenarios.keys())
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="monitoring_menu")])
    await callback.message.edit_text("📋 Сценарії для запуску:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("launch_scenario|"))
async def launch_scenario(callback: CallbackQuery, bot: Bot):
    name = callback.data.split("|", 1)[1]
    await callback.message.edit_text(f"⏳ Запуск сценарію <b>{name}</b>...", parse_mode="HTML")
    await run_monitoring_scenario(bot, name)
    await callback.message.edit_text(f"✅ Сценарій <b>{name}</b> виконано.", parse_mode="HTML")
