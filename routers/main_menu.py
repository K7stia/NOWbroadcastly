import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from keyboards.main_menu import main_menu_kb

router = Router()

WELCOME_TEXT = "Вітаю! Оберіть дію:"

# ============================
# Старт / головне меню
# ============================
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())

@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text("🏠 Повернулись до головного меню:", reply_markup=main_menu_kb())
