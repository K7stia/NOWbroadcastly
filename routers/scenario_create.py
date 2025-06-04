import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

from utils.json_storage import load_scenarios, save_scenarios
from keyboards.scenario_keyboards import (
    get_monitoring_group_keyboard,
    get_target_media_keyboard,
    get_scenario_options_keyboard,
    get_schedule_mode_keyboard,
    get_model_keyboard_for_scenarios
)
from keyboards.monitoring_keyboards import get_model_keyboard
from states.monitoring_states import ScenarioCreateState
from routers.scenario_post import post_scenarios_menu

router = Router()

def scenario_note_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустити", callback_data="skip_note")]
    ])

async def finalize_scenario_creation(state: FSMContext, message_or_callback):
    data = await state.get_data()
    name = data.pop("name")
    scenarios = load_scenarios()
    scenarios[name] = data
    save_scenarios(scenarios)

    # ⏱️ Автоматичне оновлення планувальника
    from utils.scheduler import reload_scheduler
    reload_scheduler()

    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад до сценаріїв", callback_data="scenario_menu")],
        [InlineKeyboardButton(text="🏠 На головну", callback_data="back_main")]
    ])

    msg = f"✅ Сценарій «{name}» збережено."

    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(msg, reply_markup=kb)
    elif isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(msg, reply_markup=kb)

@router.callback_query(F.data == "create_scenario")
async def scenario_create_start(callback: CallbackQuery, state: FSMContext):
    logging.debug("[TEST] ✨ create_scenario callback triggered!")
    logging.debug("[scenario] Старт створення сценарію")
    await callback.message.edit_text("🆕 Введіть назву нового сценарію:")
    await state.set_state(ScenarioCreateState.entering_name)

@router.message(ScenarioCreateState.entering_name)
async def scenario_enter_name(message: Message, state: FSMContext):
    name = message.text.strip()
    logging.debug(f"[scenario] Отримано назву: {name}")
    scenarios = load_scenarios()
    if name in scenarios:
        await message.answer("⚠️ Сценарій з такою назвою вже існує. Введіть іншу назву:")
        return
    await state.update_data(name=name, monitoring_groups=[], targets=[], rewrite=False,
                            moderation=False, skip_forwards=True, schedules=[])
    logging.debug(f"[scenario] Назву збережено. name={name}")
    await message.answer("✅ Назву збережено. Тепер виберіть джерела моніторингу:",
                         reply_markup=get_monitoring_group_keyboard(selected=[]))
    await state.set_state(ScenarioCreateState.selecting_groups)

@router.callback_query(ScenarioCreateState.selecting_groups, F.data.startswith("toggle_group_sc|"))
async def toggle_group_sc(callback: CallbackQuery, state: FSMContext):
    _, group = callback.data.split("|", 1)
    data = await state.get_data()
    selected = data.get("monitoring_groups", [])
    if group in selected:
        selected.remove(group)
    else:
        selected.append(group)
    await state.update_data(monitoring_groups=selected)
    await callback.message.edit_reply_markup(reply_markup=get_monitoring_group_keyboard(selected=selected))

@router.callback_query(ScenarioCreateState.selecting_groups, F.data == "confirm_groups_sc")
async def confirm_groups_sc(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📤 Оберіть медіа, де будемо публікувати:", reply_markup=get_target_media_keyboard(selected=[]))
    await state.set_state(ScenarioCreateState.selecting_targets)

@router.callback_query(ScenarioCreateState.selecting_targets, F.data.startswith("toggle_media_sc|"))
async def toggle_media_sc(callback: CallbackQuery, state: FSMContext):
    _, media_id_str = callback.data.split("|", 1)
    media_id = int(media_id_str)

    data = await state.get_data()
    selected = data.get("targets", [])

    exists = any(t.get("id") == media_id for t in selected)
    if exists:
        selected = [t for t in selected if t.get("id") != media_id]
    else:
        selected.append({"id": media_id})

    await state.update_data(targets=selected)
    await callback.message.edit_reply_markup(reply_markup=get_target_media_keyboard(selected=[str(t["id"]) for t in selected]))

@router.callback_query(ScenarioCreateState.selecting_targets, F.data == "confirm_targets_sc")
async def confirm_targets_sc(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.edit_text("⚙️ Оберіть опції для сценарію:", reply_markup=get_scenario_options_keyboard(
        rewrite=data.get("rewrite", False),
        moderation=data.get("moderation", False),
        skip=data.get("skip_forwards", True)))
    await state.set_state(ScenarioCreateState.selecting_options)

@router.callback_query(ScenarioCreateState.selecting_options, F.data.startswith("toggle_option_sc|"))
async def toggle_option_sc(callback: CallbackQuery, state: FSMContext):
    _, opt = callback.data.split("|", 1)
    data = await state.get_data()
    new_val = not data.get(opt, False)
    await state.update_data({opt: new_val})
    updated = await state.get_data()
    await callback.message.edit_reply_markup(reply_markup=get_scenario_options_keyboard(
        rewrite=updated.get("rewrite"),
        moderation=updated.get("moderation"),
        skip=updated.get("skip_forwards")))

@router.callback_query(ScenarioCreateState.selecting_options, F.data == "confirm_options_sc")
async def confirm_options_sc(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🤖 Оберіть модель моніторингу:", reply_markup=get_model_keyboard_for_scenarios())
    await state.set_state(ScenarioCreateState.selecting_model)

@router.callback_query(ScenarioCreateState.selecting_model, F.data.startswith("manual_model|"))
async def select_monitoring_model(callback: CallbackQuery, state: FSMContext):
    _, model = callback.data.split("|", 1)
    await state.update_data(model=model, monitoring_model=model)
    logging.debug(f"[scenario] ✅ Обрано модель: {model}")
    await callback.message.edit_text("🕓 Оберіть режим запуску сценарію:", reply_markup=get_schedule_mode_keyboard())
    await state.set_state(ScenarioCreateState.selecting_schedule_mode)

@router.callback_query(ScenarioCreateState.selecting_model, F.data == "manual_monitoring")
async def go_back_from_model(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.edit_text(
        "⚙️ Оберіть опції для сценарію:",
        reply_markup=get_scenario_options_keyboard(
            rewrite=data.get("rewrite", False),
            moderation=data.get("moderation", False),
            skip=data.get("skip_forwards", True)
        )
    )
    await state.set_state(ScenarioCreateState.selecting_options)
    logging.debug("[scenario] ↩️ Повернення до selecting_options")

@router.callback_query(ScenarioCreateState.selecting_schedule_mode, F.data.startswith("schedule_mode_sc|"))
async def handle_schedule_mode_sc(callback: CallbackQuery, state: FSMContext):
    _, mode = callback.data.split("|", 1)
    await state.update_data(current_schedule_mode=mode)
    if mode == "fixed_times":
        await callback.message.edit_text("⏰ Введіть час (у форматі HH:MM):")
        await state.set_state(ScenarioCreateState.entering_fixed_time)
    elif mode in ["random_in_intervals", "loop_in_intervals"]:
        await callback.message.edit_text("🕒 Введіть початок інтервалу (у форматі HH:MM):")
        await state.set_state(ScenarioCreateState.entering_interval_start)

@router.message(ScenarioCreateState.entering_fixed_time)
async def enter_fixed_time(message: Message, state: FSMContext):
    time = message.text.strip()
    data = await state.get_data()
    schedules = data.get("schedules", [])
    for s in schedules:
        if s["type"] == "fixed_times":
            s["times"].append(time)
            break
    else:
        schedules.append({"type": "fixed_times", "times": [time]})
    await state.update_data(schedules=schedules)
    await message.answer("📝 Введіть опис або нотатку для сценарію (або натисніть 'Пропустити'):", reply_markup=scenario_note_keyboard())
    await state.set_state(ScenarioCreateState.entering_note)

@router.message(ScenarioCreateState.entering_interval_start)
async def enter_interval_start(message: Message, state: FSMContext):
    start = message.text.strip()
    await state.update_data(interval_start=start)
    await message.answer("🕓 Введіть кінець інтервалу (у форматі HH:MM):")
    await state.set_state(ScenarioCreateState.entering_interval_end)

@router.message(ScenarioCreateState.entering_interval_end)
async def enter_interval_end(message: Message, state: FSMContext):
    end = message.text.strip()
    data = await state.get_data()
    mode = data.get("current_schedule_mode")
    schedules = data.get("schedules", [])
    interval = {"start": data.get("interval_start"), "end": end}

    if mode == "random_in_intervals":
        for s in schedules:
            if s["type"] == "random_in_intervals":
                s["intervals"].append(interval)
                break
        else:
            schedules.append({"type": "random_in_intervals", "intervals": [interval]})
        await state.update_data(schedules=schedules)
        await message.answer("📝 Введіть опис або нотатку для сценарію (або натисніть 'Пропустити'):", reply_markup=scenario_note_keyboard())
        await state.set_state(ScenarioCreateState.entering_note)

    elif mode == "loop_in_intervals":
        await state.update_data(interval_end=end)
        await message.answer("🔁 Введіть інтервал повторення в хвилинах (наприклад: 3):")
        await state.set_state(ScenarioCreateState.entering_loop_delay)

@router.message(ScenarioCreateState.entering_loop_delay)
async def enter_loop_delay(message: Message, state: FSMContext):
    delay = int(message.text.strip())
    data = await state.get_data()
    schedules = data.get("schedules", [])
    interval = {"start": data.get("interval_start"), "end": data.get("interval_end")}
    for s in schedules:
        if s["type"] == "loop_in_intervals":
            s["intervals"].append(interval)
            s["interval_min"] = delay
            s["interval_max"] = delay
            break
    else:
        schedules.append({"type": "loop_in_intervals", "intervals": [interval], "interval_min": delay, "interval_max": delay})
    await state.update_data(schedules=schedules)
    await message.answer("📝 Введіть опис або нотатку для сценарію (або натисніть 'Пропустити'):", reply_markup=scenario_note_keyboard())
    await state.set_state(ScenarioCreateState.entering_note)

@router.message(ScenarioCreateState.entering_note)
async def enter_note(message: Message, state: FSMContext):
    await state.update_data(note=message.text.strip())
    await finalize_scenario_creation(state, message)

@router.callback_query(ScenarioCreateState.entering_note, F.data == "skip_note")
async def skip_note(callback: CallbackQuery, state: FSMContext):
    await state.update_data(note="-")
    await finalize_scenario_creation(state, callback)

@router.callback_query(F.data == "list_scenarios")
async def list_scenarios(callback: CallbackQuery, state: FSMContext, bot):
    await post_scenarios_menu(callback)

@router.callback_query(ScenarioCreateState.selecting_model, F.data.startswith("scenario_model|"))
async def select_scenario_model(callback: CallbackQuery, state: FSMContext):
    _, model = callback.data.split("|", 1)
    await state.update_data(model=model)
    await callback.message.edit_text("🕓 Оберіть режим запуску сценарію:", reply_markup=get_schedule_mode_keyboard())
    await state.set_state(ScenarioCreateState.selecting_schedule_mode)

@router.callback_query(ScenarioCreateState.selecting_model, F.data == "scenario_back_to_options")
async def back_to_options_from_model(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.edit_text(
        "⚙️ Оберіть опції для сценарію:",
        reply_markup=get_scenario_options_keyboard(
            rewrite=data.get("rewrite", False),
            moderation=data.get("moderation", False),
            skip=data.get("skip_forwards", True)
        )
    )
    await state.set_state(ScenarioCreateState.selecting_options)
