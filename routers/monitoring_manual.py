import re
import os
import html
import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from aiogram.fsm.context import FSMContext

from states.monitoring_states import ManualMonitorState, SourceSignatureState
from keyboards.monitoring_keyboards import get_category_keyboard, get_model_keyboard
from keyboards.monitoring import monitoring_mode_kb, monitoring_target_kb, monitoring_options_kb
from utils.json_storage import (
    load_monitoring_groups,
    load_config,
    load_groups,
    get_trim_settings,
    load_media
)
from utils.monitoring_utils import build_channels_with_id, build_full_caption, filter_posts_by_stop_words
from utils.rewrite import rewrite_text
from routers.monitoring_moderation import send_post_to_moderation
from monitoring_models import model_registry
from utils.telethon_fetcher import forward_post_to_staging, fetch_posts_for_category
from utils.facebook_utils import prepare_facebook_post
from utils.facebook_publisher import publish_to_facebook 
from utils.instagram_utils import prepare_instagram_post
from utils.instagram_publisher import publish_to_instagram
from utils.monitoring_launcher import manual_monitor_launch

router = Router()

@router.callback_query(F.data == "manual_monitoring")
async def manual_monitoring_entry(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ManualMonitorState.selecting_category)
    await callback.message.edit_text("📂 Виберіть категорію моніторингу:", reply_markup=get_category_keyboard())

@router.callback_query(F.data.startswith("manual_select_category|"))
async def manual_select_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("|", 1)[1]
    await state.update_data(category=category)
    await state.set_state(ManualMonitorState.selecting_model)
    await callback.message.edit_text(
        f"🧠 Обрано категорію: <b>{category}</b>\n\nВиберіть модель моніторингу:",
        reply_markup=get_model_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("manual_model|"))
async def manual_model_selected(callback: CallbackQuery, state: FSMContext):
    model = callback.data.split("|", 1)[1]
    await state.update_data(model=model)
    await state.set_state(ManualMonitorState.selecting_publish_mode)
    await callback.message.edit_text("Оберіть куди публікувати результати моніторингу:", reply_markup=monitoring_mode_kb())

@router.callback_query(F.data.startswith("monitor_mode|"))
async def monitor_select_mode(callback: CallbackQuery, state: FSMContext):
    mode = callback.data.split("|", 1)[1]
    groups = load_groups()
    channels = load_media()
    await state.update_data({"selected_channels": [], "selected_groups": [], "publish_mode": mode})

    if mode == "channels" and not channels:
        await callback.answer("❗️ Немає доступних каналів.", show_alert=True)
        return
    if mode == "groups" and not groups:
        await callback.answer("❗️ Немає доступних груп.", show_alert=True)
        return
    if mode == "mix" and not groups and not channels:
        await callback.answer("❗️ Немає каналів або груп для вибору.", show_alert=True)
        return

    await state.set_state(ManualMonitorState.selecting_targets)
    await callback.message.edit_text(
        "📡 Оберіть медіа або групу для публікації:\n\n"
        "📢 – Telegram канали\n"
        "📘 – Facebook сторінки"
        "📸 – Instagram профілі\n",
      #  "🐦 – Twitter акаунти",
        reply_markup=monitoring_target_kb(
            channels=channels if mode != "groups" else {},
            groups=groups if mode != "channels" else {},
            selected_channels=[],
            selected_groups=[],
            show_channels=(mode in ["channels", "mix"]),
            show_groups=(mode in ["groups", "mix"])
        )
    )

@router.callback_query(F.data == "monitor_proceed_targets")
async def proceed_to_monitoring_settings(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ManualMonitorState.toggle_moderation)
    await state.update_data(moderation=False, rewrite=False, skip_forwards=True)
    data = await state.get_data()
    
    await callback.message.edit_text(
        "🛠 Налаштування перед запуском:",
        reply_markup=monitoring_options_kb(
            data.get("moderation", False),
            data.get("rewrite", False),
            data.get("skip_forwards", True)
        )
    )

@router.callback_query(F.data == "toggle_moderation")
async def toggle_moderation(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_val = not data.get("moderation", False)
    await state.update_data(moderation=new_val)
    await callback.message.edit_reply_markup(reply_markup=monitoring_options_kb(new_val, data.get("rewrite", False)))
    await callback.answer()

@router.callback_query(F.data == "toggle_rewrite")
async def toggle_rewrite(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_val = not data.get("rewrite", False)
    await state.update_data(rewrite=new_val)
    await callback.message.edit_reply_markup(reply_markup=monitoring_options_kb(data.get("moderation", False), new_val))
    await callback.answer()

@router.callback_query(F.data == "toggle_skip_forwards")
async def toggle_skip_forwards(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_val = not data.get("skip_forwards", True)
    await state.update_data(skip_forwards=new_val)
    await callback.message.edit_reply_markup(reply_markup=monitoring_options_kb(
        data.get("moderation", False),
        data.get("rewrite", False),
        new_val
    ))
    await callback.answer()

@router.callback_query(F.data.startswith("manual_toggle_channel|"))
async def toggle_channel(callback: CallbackQuery, state: FSMContext):
    channel = callback.data.split("|", 1)[1]
    data = await state.get_data()
    selected_channels = set(data.get("selected_channels", []))
    selected_groups = set(data.get("selected_groups", []))
    mode = data.get("publish_mode", "mix")

    if channel in selected_channels:
        selected_channels.remove(channel)
    else:
        selected_channels.add(channel)

    await state.update_data(selected_channels=list(selected_channels))
    await callback.message.edit_reply_markup(reply_markup=monitoring_target_kb(
        channels=load_media() if mode != "groups" else {},
        groups=load_groups() if mode != "channels" else {},
        selected_channels=selected_channels,
        selected_groups=selected_groups,
        show_channels=(mode in ["channels", "mix"]),
        show_groups=(mode in ["groups", "mix"])
    ))
    await callback.answer()

@router.callback_query(F.data.startswith("manual_toggle_group|"))
async def toggle_group(callback: CallbackQuery, state: FSMContext):
    group = callback.data.split("|", 1)[1]
    data = await state.get_data()
    selected_groups = set(data.get("selected_groups", []))
    selected_channels = set(data.get("selected_channels", []))
    mode = data.get("publish_mode", "mix")

    if group in selected_groups:
        selected_groups.remove(group)
    else:
        selected_groups.add(group)

    await state.update_data(selected_groups=list(selected_groups))
    await callback.message.edit_reply_markup(reply_markup=monitoring_target_kb(
        channels=load_media() if mode != "groups" else {},
        groups=load_groups() if mode != "channels" else {},
        selected_channels=selected_channels,
        selected_groups=selected_groups,
        show_channels=(mode in ["channels", "mix"]),
        show_groups=(mode in ["groups", "mix"])
    ))
    await callback.answer()

@router.callback_query(F.data == "manual_monitor_launch")
async def launch_manual_monitoring(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await manual_monitor_launch(callback, state, bot)
