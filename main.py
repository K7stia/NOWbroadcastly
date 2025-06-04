import asyncio
import logging

import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from utils.telethon_client import client as telethon_client
from utils.access_control import IsAdmin
from utils.scheduler import scheduler, init_scenarios_cron_jobs, set_scheduler_bot

# 🔧 Logging config – одразу після імпортів
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Завантажити змінні з .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Імпортуємо роутери
from routers import (
    main_menu,
    publish,
    groups,
    channel_signature,
    menu_media,  # ✅ Замінили menu_channels на menu_media
    admin_panel,
    monitoring_manual,
    monitoring_menu,
    monitoring_rewrite,
    monitoring_categories,
    scenario_menu,
    scenario_create,
    scenario_post
)

async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing in .env file!")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    bot.client = telethon_client 

    dp = Dispatcher(storage=MemoryStorage())

    # Глобальні фільтри доступу
    dp.message.filter(IsAdmin())
    dp.callback_query.filter(IsAdmin())

    # Підключення роутерів
    dp.include_router(main_menu.router)
    dp.include_router(publish.router)
    dp.include_router(groups.router)
    dp.include_router(channel_signature.router)
    dp.include_router(menu_media.router)
    dp.include_router(admin_panel.router)
    dp.include_router(monitoring_manual.router)
    dp.include_router(monitoring_menu.router)
    dp.include_router(monitoring_rewrite.router)
    dp.include_router(monitoring_categories.router)
    dp.include_router(scenario_menu.router)
    dp.include_router(scenario_create.router)
    dp.include_router(scenario_post.router)

    # 🔄 Ініціалізуємо планувальник
    scheduler.start()
    init_scenarios_cron_jobs()
    set_scheduler_bot(bot)
    
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.client.start()
    await dp.start_polling(bot)

# 🟢 Запуск
if __name__ == "__main__":
    asyncio.run(main())
