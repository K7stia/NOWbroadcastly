import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from keyboards.scenario_keyboards import get_monitoring_group_keyboard, scenario_menu_keyboard
from states.monitoring_states import ScenarioCreateState
from routers.scenario_activate import router as activate_router

router = Router()
router.include_router(activate_router)

@router.callback_query(F.data == "scenario_menu")
async def show_scenario_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 Сценарії публікацій — обери дію:",
        reply_markup=scenario_menu_keyboard()
    )



