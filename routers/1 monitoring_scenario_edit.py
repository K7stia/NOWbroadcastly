from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from utils.json_storage import load_monitoring_groups, load_scenarios, save_scenarios

router = Router()

class NewScenarioState(StatesGroup):
    waiting_name = State()
    waiting_category = State()
    waiting_model = State()
    waiting_output_channel = State()
    toggle_moderation = State()
    toggle_rewrite = State()

@router.callback_query(F.data == "create_scenario")
async def start_create_scenario(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(NewScenarioState.waiting_name)
    await callback.message.edit_text("✍️ Введіть назву нового сценарію:")

@router.message(NewScenarioState.waiting_name)
async def scenario_name_entered(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("❗️ Назва не може бути порожньою.")
        return

    scenarios = load_scenarios()
    if name in scenarios:
        await message.answer("⚠️ Сценарій з такою назвою вже існує.")
        return

    await state.update_data(name=name)
    await state.set_state(NewScenarioState.waiting_category)

    categories = load_monitoring_groups().keys()
    if not categories:
        await message.answer("❗️ Немає доступних категорій моніторингу.")
        await state.clear()
        return

    buttons = [[InlineKeyboardButton(text=cat, callback_data=f"select_scenario_category|{cat}")] for cat in sorted(categories)]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("📂 Виберіть категорію моніторингу:", reply_markup=kb)

@router.callback_query(F.data.startswith("select_scenario_category|"))
async def select_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("|", 1)[1]
    await state.update_data(category=category)
    await state.set_state(NewScenarioState.waiting_model)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Популярне", callback_data="model|popular")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="create_scenario")]
    ])
    await callback.message.edit_text("🧠 Виберіть модель моніторингу:", reply_markup=kb)

@router.callback_query(F.data.startswith("model|"))
async def select_model(callback: CallbackQuery, state: FSMContext):
    model = callback.data.split("|", 1)[1]
    await state.update_data(model=model)
    await state.set_state(NewScenarioState.waiting_output_channel)
    await callback.message.edit_text("📤 Введіть @username або ID каналу для публікації:")

@router.message(NewScenarioState.waiting_output_channel)
async def output_channel_entered(message: Message, state: FSMContext):
    val = message.text.strip()
    if not val:
        await message.answer("❗️ Введіть коректне значення.")
        return

    await state.update_data(output_channel=val, moderation=True, rewrite=False)
    await show_scenario_settings(message, state)

@router.callback_query(F.data == "toggle_scenario_moderation")
async def toggle_moderation(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(moderation=not data.get("moderation", True))
    await show_scenario_settings(callback.message, state)

@router.callback_query(F.data == "toggle_scenario_rewrite")
async def toggle_rewrite(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(rewrite=not data.get("rewrite", False))
    await show_scenario_settings(callback.message, state)

@router.callback_query(F.data == "save_scenario")
async def save_scenario(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    scenarios = load_scenarios()
    scenarios[name] = {
        "category": data["category"],
        "model": data["model"],
        "output_channel": data["output_channel"],
        "moderation": data["moderation"],
        "rewrite": data["rewrite"]
    }
    save_scenarios(scenarios)
    await state.clear()
    await callback.message.edit_text(f"✅ Сценарій <b>{name}</b> збережено!", parse_mode="HTML")

async def show_scenario_settings(message_or_callback, state: FSMContext):
    data = await state.get_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🛡 Модерація: {'✅' if data.get('moderation') else '❌'}", callback_data="toggle_scenario_moderation")],
        [InlineKeyboardButton(text=f"✍️ Рерайт: {'✅' if data.get('rewrite') else '❌'}", callback_data="toggle_scenario_rewrite")],
        [InlineKeyboardButton(text="💾 Зберегти сценарій", callback_data="save_scenario")]
    ])
    text = (
        f"📝 Налаштування сценарію:

"
        f"Назва: <b>{data.get('name')}</b>\n"
        f"Категорія: <code>{data.get('category')}</code>\n"
        f"Модель: <code>{data.get('model')}</code>\n"
        f"Канал: <code>{data.get('output_channel')}</code>\n"
        f"Модерація: {'✅' if data.get('moderation') else '❌'}\n"
        f"Рерайт: {'✅' if data.get('rewrite') else '❌'}"
    )
    await message_or_callback.answer(text, parse_mode="HTML", reply_markup=kb) if isinstance(message_or_callback, Message) else message_or_callback.edit_text(text, parse_mode="HTML", reply_markup=kb)
