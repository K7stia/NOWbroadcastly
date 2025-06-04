from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils.json_storage import load_scenarios, save_scenarios

router = Router()

@router.callback_query(F.data == "list_scenarios")
async def list_scenarios(callback: CallbackQuery):
    scenarios = load_scenarios()
    if not scenarios:
        await callback.message.edit_text("❗️ Сценарії ще не створено.")
        return

    buttons = [
        [InlineKeyboardButton(text=f"✏️ {name}", callback_data=f"edit_scenario|{name}"),
         InlineKeyboardButton(text="🗑", callback_data=f"delete_scenario|{name}")]
        for name in sorted(scenarios.keys())
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="monitoring_automation")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("📋 Оберіть сценарій для редагування або видалення:", reply_markup=kb)

@router.callback_query(F.data.startswith("delete_scenario|"))
async def delete_scenario(callback: CallbackQuery):
    name = callback.data.split("|", 1)[1]
    scenarios = load_scenarios()
    if name in scenarios:
        del scenarios[name]
        save_scenarios(scenarios)
        await callback.answer("✅ Сценарій видалено.")
    await list_scenarios(callback)

# ✏️ Редагування сценарію - перенаправляємо в flow створення зі старими даними (опціонально можна реалізувати пізніше)
