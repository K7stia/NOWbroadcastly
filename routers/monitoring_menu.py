from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.monitoring_menu import monitoring_menu_kb
from keyboards.scenario_keyboards import scenario_menu_keyboard

router = Router()

@router.callback_query(F.data == "monitoring_menu")
async def show_monitoring_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🧠 Меню моніторингу публікацій:",
        reply_markup=monitoring_menu_kb()
    )

@router.callback_query(F.data == "monitoring_config")
async def open_monitoring_config(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛡 Змінити групу модерації", callback_data="edit_group_id")],
        [InlineKeyboardButton(text="✍️ Рерайт", callback_data="edit_rewrite_style")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="monitoring_menu")]
    ])
    await callback.message.edit_text("⚙️ Оберіть налаштування:", reply_markup=kb)

@router.callback_query(F.data == "monitoring_logs")
async def monitoring_logs_placeholder(callback: CallbackQuery):
    await callback.message.edit_text("📜 Тут згодом буде журнал запусків моніторингу.")

