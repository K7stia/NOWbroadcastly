from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from utils.json_storage import load_config, save_config

router = Router()

class RewriteState(StatesGroup):
    waiting_style = State()

@router.callback_query(F.data == "edit_rewrite_style")
async def prompt_rewrite_style(callback: CallbackQuery, state: FSMContext):
    config = load_config()
    current = config.get("rewrite_style", "не задано")

    await state.set_state(RewriteState.waiting_style)
    await callback.message.edit_text(
        f"✍️ Введіть інструкцію, як має виглядати рерайт тексту:\n\n"
        f"<i>Поточна інструкція:</i>\n<code>{current}</code>\n\n"
        "Наприклад: \"Зроби текст коротшим, інформативним і неформальним.\"",
        parse_mode="HTML"
    )

@router.message(RewriteState.waiting_style)
async def save_rewrite_style(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer("❗️ Інструкція не може бути порожньою.")
        return

    config = load_config()
    config["rewrite_style"] = text
    save_config(config)
    await state.clear()
    await message.answer("✅ Стиль рерайту оновлено.")
