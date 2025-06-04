from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from utils.access_control import load_allowed_users, add_user, remove_user, SUPER_ADMIN_ID

router = Router()

class AdminState(StatesGroup):
    waiting_user_id = State()

@router.callback_query(F.data == "admin_menu")
async def open_admin_menu(callback: CallbackQuery):
    users = load_allowed_users()
    buttons = [
        [InlineKeyboardButton(text=f"❌ Видалити {uid}", callback_data=f"remove_user|{uid}")]
        for uid in users if uid != SUPER_ADMIN_ID
    ]
    buttons.append([InlineKeyboardButton(text="➕ Додати ID", callback_data="add_user")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])

    await callback.message.edit_text("⚙️ Управління доступом:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "add_user")
async def add_user_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_user_id)
    await callback.message.edit_text(
        "👤 Додати користувача до доступу:\n\n"
        "• Перешліть повідомлення від користувача\n"
        "• або введіть @username\n"
        "• або введіть Telegram ID"
    )

@router.message(AdminState.waiting_user_id)
async def process_user_id(message: Message, state: FSMContext):
    # Готова клавіатура для після додавання
    reply_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Додати ще користувача", callback_data="add_user")],
        [InlineKeyboardButton(text="🏠 Головне меню", callback_data="back_main")]
    ])

    # Якщо переслане повідомлення — додаємо forward_from
    if message.forward_from:
        user = message.forward_from
        user_id = user.id
        add_user(user_id)
        await message.answer(
            f"✅ Додано: {user.username or 'Без username'} (ID: {user_id}) через переслане повідомлення",
            reply_markup=reply_kb
        )
        await state.clear()
        return

    raw = message.text.strip()

    if raw.startswith("@"):
        try:
            chat = await message.bot.get_chat(raw)
            if chat.type != "private":
                await message.answer("❗️ Це не приватний користувач. Введіть @username або ID реального користувача.")
                await state.clear()
                return

            user_id = chat.id
            add_user(user_id)
            await message.answer(
                f"✅ Додано: {chat.username or 'Без username'} (ID: {user_id})",
                reply_markup=reply_kb
            )
        except Exception:
            await message.answer(
                "❗️ Не вдалося отримати ID за username.\n"
                "Можливі причини:\n"
                "– Користувач не писав боту\n"
                "– Username введено з помилкою\n\n"
                "Рекомендуємо попросити користувача написати /start боту."
            )
    else:
        try:
            user_id = int(raw)
            add_user(user_id)
            await message.answer(
                f"✅ Додано користувача з ID: {user_id}",
                reply_markup=reply_kb
            )
        except ValueError:
            await message.answer("❗️ Введіть @username, ID або перешліть повідомлення від користувача.")

    await state.clear()

@router.callback_query(F.data.startswith("remove_user|"))
async def remove_user_callback(callback: CallbackQuery):
    user_id = int(callback.data.split("|")[1])
    remove_user(user_id)
    await open_admin_menu(callback)
