import json
import logging
from aiogram import Bot
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from utils.json_storage import load_scenarios, save_scenarios
from utils.monitoring_utils import run_monitoring_scenario

router = Router()

@router.callback_query(F.data == "post_scenarios")
async def post_scenarios_menu(callback: CallbackQuery):
    scenarios = load_scenarios()
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"scenario_manage_scpost|{name}")]
        for name in scenarios.keys()
    ]
    buttons.append([InlineKeyboardButton(text="▶️ Ручний запуск", callback_data="scenario_manual_run_scpost")])
    buttons.append([InlineKeyboardButton(text="🔄 Оновити планувальник", callback_data="reload_scheduler_manual")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="scenario_menu")])
    await callback.message.edit_text("📅 Сценарії публікацій:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("scenario_manage_scpost|"))
async def manage_scenario_scpost(callback: CallbackQuery):
    parts = callback.data.split("|")
    name = parts[1]
    back_to = parts[2] if len(parts) > 2 else "post_scenarios"

    scenarios = load_scenarios()
    sc = scenarios.get(name, {})
    text = f"📄 <b>{name}</b>\n\n📍 Джерел: {len(sc.get('monitoring_groups', []))}\n📤 Медій: {len(sc.get('targets', []))}\n⚙️ Рерайт: {sc.get('rewrite', False)} | Модерація: {sc.get('moderation', False)} | Пропускати репости: {sc.get('skip_forwards', True)}\n📝 {sc.get('note', '-')[:100]}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Запустити зараз", callback_data=f"scenario_run_scpost|{name}|{back_to}")],
        [InlineKeyboardButton(text="🗑 Видалити", callback_data=f"scenario_delete_scpost|{name}|{back_to}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=back_to)]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("scenario_run_scpost|"))
async def run_scenario_now_scpost(callback: CallbackQuery, bot: Bot, state: FSMContext):
    _, name, back_to = callback.data.split("|", 2)
    scenarios = load_scenarios()
    sc = scenarios.get(name)

    if not sc:
        await callback.answer("❌ Сценарій не знайдено.", show_alert=True)
        return

    logging.info(f"[Scenario] ▶️ Manual run of scenario: {name}")
    await callback.answer(f"▶️ Запускаю сценарій: {name}")

    from utils.monitoring_utils import launch_monitoring_from_dict
    await launch_monitoring_from_dict(sc, callback, bot)

    await callback.message.edit_text(
        f"✅ Сценарій <b>{name}</b> виконано.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=back_to)],
            [InlineKeyboardButton(text="🏠 На головну", callback_data="back_main")]
        ])
    )

@router.callback_query(F.data == "reload_scheduler_manual")
async def reload_scheduler_manual(callback: CallbackQuery):
    from utils.scheduler import reload_scheduler
    reload_scheduler()
    await callback.answer("🔄 Планувальник оновлено", show_alert=True)

@router.callback_query(F.data.startswith("scenario_delete_scpost|"))
async def delete_scenario_scpost(callback: CallbackQuery):
    _, name, back_to = callback.data.split("|", 2)
    scenarios = load_scenarios()
    if name in scenarios:
        del scenarios[name]
        save_scenarios(scenarios)
        await callback.message.edit_text(
            f"🗑 Сценарій '{name}' видалено.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data=back_to)],
                [InlineKeyboardButton(text="🏠 На головну", callback_data="back_main")]
            ])
        )
    else:
        await callback.message.edit_text("❌ Сценарій не знайдено.")


@router.callback_query(F.data == "scenario_manual_run_scpost")
async def manual_run_menu_scpost(callback: CallbackQuery):
    scenarios = load_scenarios()
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"scenario_run_scpost|{name}")]
        for name in scenarios.keys()
    ] + [[InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]]
    await callback.message.edit_text("▶️ Виберіть сценарій для ручного запуску:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
