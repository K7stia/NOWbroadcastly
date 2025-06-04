from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from utils.json_storage import load_config, save_config

router = Router()

class ConfigState(StatesGroup):
    waiting_group_id = State()

@router.callback_query(F.data == "monitoring_config")
async def open_config_menu(callback: CallbackQuery):
    config = load_config()
    group_id = config.get("moderation_group_id", "не встановлено")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛡 Змінити групу модерації", callback_data="edit_group_id")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="monitoring_menu")]
    ])

    await callback.message.edit_text(
        f"⚙️ <b>Налаштування модерації</b>\n\n"
        f"Поточна група модерації: <code>{group_id}</code>",
        reply_markup=kb,
        parse_mode="HTML"
    )

@router.callback_query(F.data == "edit_group_id")
async def ask_new_group_id(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ConfigState.waiting_group_id)
    await callback.message.edit_text("🛡 Введіть новий ID групи модерації (наприклад -1001234567890):")

@router.message(ConfigState.waiting_group_id)
async def save_new_group_id(message: Message, state: FSMContext):
    raw = message.text.strip()
    try:
        group_id = int(raw)
        config = load_config()
        config["moderation_group_id"] = group_id
        save_config(config)
        await state.clear()
        await message.answer(f"✅ Групу модерації оновлено: <code>{group_id}</code>", parse_mode="HTML")
    except ValueError:
        await message.answer("❗️ Введіть коректний числовий ID групи.")
