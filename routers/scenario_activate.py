from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils.json_storage import load_scenarios, save_scenarios

router = Router()

@router.callback_query(F.data == "activate_scenarios")
async def activate_scenarios_menu(callback: CallbackQuery):
    scenarios = load_scenarios()
    buttons = []
    for name, data in scenarios.items():
        active = data.get("active", False)
        status = "✅" if active else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {name}",
            callback_data=f"toggle_scenario_active|{name}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="scenario_menu")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("⚙️ Активація сценаріїв:", reply_markup=markup)

@router.callback_query(F.data.startswith("toggle_scenario_active|"))
async def toggle_scenario_active(callback: CallbackQuery):
    _, name = callback.data.split("|", 1)
    scenarios = load_scenarios()
    if name in scenarios:
        current = scenarios[name].get("active", False)
        scenarios[name]["active"] = not current
        save_scenarios(scenarios)

        # 🔄 Оновлюємо планувальник після зміни активності
        from utils.scheduler import reload_scheduler
        reload_scheduler()
        
    await activate_scenarios_menu(callback)
