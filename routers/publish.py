import logging, html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from states.publish import PublishNews
from keyboards.publish import publish_target_kb, publish_options_kb, publish_mode_kb
from utils.json_storage import load_groups, load_known_media, load_channel_signature
from utils.facebook_publisher import publish_to_facebook

router = Router()

@router.callback_query(F.data == "publish_news")
async def cb_publish_news(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Оберіть режим публікації:", reply_markup=publish_mode_kb())

@router.callback_query(F.data.startswith("select_mode|"))
async def cb_select_mode(callback: CallbackQuery, state: FSMContext):
    mode = callback.data.split("|", 1)[1]
    groups = load_groups()
    media = load_known_media()
    await state.set_data({"selected_channels": [], "selected_groups": [], "publish_mode": mode})

    if mode == "channels":
        if not media:
            await callback.answer("❗️ Немає доступних медіа.", show_alert=True)
            return
        await callback.message.edit_text("Оберіть медіа:", reply_markup=publish_target_kb(
            channels=media, groups={}, selected_channels=[], selected_groups=[], show_channels=True, show_groups=False
        ))

    elif mode == "groups":
        if not groups:
            await callback.answer("❗️ Немає доступних груп.", show_alert=True)
            return
        await callback.message.edit_text("Оберіть групу(и):", reply_markup=publish_target_kb(
            channels={}, groups=groups, selected_channels=[], selected_groups=[], show_channels=False, show_groups=True
        ))

    else:  # mix
        if not groups and not media:
            await callback.answer("❗️ Немає медіа або груп для вибору.", show_alert=True)
            return
        await callback.message.edit_text("Оберіть місця для публікації:", reply_markup=publish_target_kb(
            channels=media, groups=groups, selected_channels=[], selected_groups=[], show_channels=True, show_groups=True
        ))

@router.callback_query(F.data.startswith("toggle_group|"))
async def toggle_group(callback: CallbackQuery, state: FSMContext):
    group_name = callback.data.split("|", 1)[1]
    data = await state.get_data()
    selected_groups = set(data.get("selected_groups", []))
    selected_channels = set(data.get("selected_channels", []))
    publish_mode = data.get("publish_mode", "mix")

    if group_name in selected_groups:
        selected_groups.remove(group_name)
    else:
        selected_groups.add(group_name)

    await state.update_data(selected_groups=list(selected_groups))
    await callback.message.edit_reply_markup(reply_markup=publish_target_kb(
        channels=load_known_media() if publish_mode != "groups" else {},
        groups=load_groups() if publish_mode != "channels" else {},
        selected_channels=selected_channels,
        selected_groups=selected_groups,
        show_channels=(publish_mode in ["channels", "mix"]),
        show_groups=(publish_mode in ["groups", "mix"])
    ))
    await callback.answer()

@router.callback_query(F.data.startswith("toggle_channel|"))
async def toggle_channel(callback: CallbackQuery, state: FSMContext):
    channel = callback.data.split("|", 1)[1]
    data = await state.get_data()
    selected_channels = set(data.get("selected_channels", []))
    selected_groups = set(data.get("selected_groups", []))
    publish_mode = data.get("publish_mode", "mix")

    if channel in selected_channels:
        selected_channels.remove(channel)
    else:
        selected_channels.add(channel)

    await state.update_data(selected_channels=list(selected_channels))
    await callback.message.edit_reply_markup(reply_markup=publish_target_kb(
        channels=load_known_media() if publish_mode != "groups" else {},
        groups=load_groups() if publish_mode != "channels" else {},
        selected_channels=selected_channels,
        selected_groups=selected_groups,
        show_channels=(publish_mode in ["channels", "mix"]),
        show_groups=(publish_mode in ["groups", "mix"])
    ))
    await callback.answer()

@router.callback_query(F.data == "proceed_to_content")
async def proceed_to_content(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    groups = load_groups()
    all_ids = set(data.get("selected_channels", []))

    for group in data.get("selected_groups", []):
        for ch in groups.get(group, []):
            all_ids.add(str(ch["id"]))

    known = load_known_media()
    targets = []
    for id_str in all_ids:
        info = known.get(id_str)
        if info and "id" in info:
            targets.append({"id": info["id"], "title": info.get("title", id_str), "platform": info.get("platform", "telegram")})

    await state.update_data(channels=targets, use_signature=True, sound_on=True)
    await state.set_state(PublishNews.waiting_content)
    await callback.message.edit_text("Відправте новину для публікації. Це може бути текст або медіа. Для скасування натисніть /cancel")

@router.message(PublishNews.waiting_content)
async def handle_content(message: Message, state: FSMContext):
    data_to_store = {}
    if message.text and not message.media_group_id:
        data_to_store["text"] = message.html_text or ""
    elif message.photo:
        data_to_store["photo_file_id"] = message.photo[-1].file_id
        if message.caption:
            data_to_store["caption"] = message.html_text
    elif message.video:
        data_to_store["video_file_id"] = message.video.file_id
        if message.caption:
            data_to_store["caption"] = message.html_text
    else:
        await message.answer("❗️ Непідтримуваний формат. Надішліть текст, фото або відео.")
        return

    await state.update_data(**data_to_store)
    opts = await state.get_data()
    await state.set_state(PublishNews.waiting_options)
    await message.answer("Налаштування перед публікацією:", reply_markup=publish_options_kb(opts.get("sound_on", True), opts.get("use_signature", False)))

@router.callback_query(PublishNews.waiting_options, F.data == "toggle_sound")
async def cb_toggle_sound(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_val = not data.get("sound_on", True)
    await state.update_data(sound_on=new_val)
    await callback.message.edit_reply_markup(reply_markup=publish_options_kb(new_val, data.get("use_signature", False)))
    await callback.answer()

@router.callback_query(PublishNews.waiting_options, F.data == "toggle_signature")
async def cb_toggle_signature(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_val = not data.get("use_signature", False)
    await state.update_data(use_signature=new_val)
    await callback.message.edit_reply_markup(reply_markup=publish_options_kb(data.get("sound_on", True), new_val))
    await callback.answer()

@router.callback_query(PublishNews.waiting_options, F.data == "publish_now")
async def cb_publish_now(callback: CallbackQuery, state: FSMContext, bot):
    data = await state.get_data()
    targets = data.get("channels", [])
    use_signature = data.get("use_signature", False)
    sound_on = data.get("sound_on", True)
    disable_notif = not sound_on
    failed = []

    for target in targets:
        chat_id = target["id"]
        title = target["title"]
        platform = target.get("platform", "telegram")
        sig_info = load_channel_signature(chat_id)
        raw_sig = sig_info.get("signature", "")
        sig_text = f"\n\n{raw_sig}" if platform == "telegram" and use_signature and sig_info.get("enabled", True) and raw_sig else ""

        try:
            if platform == "telegram":
                if "text" in data:
                    await bot.send_message(chat_id, data["text"] + sig_text, parse_mode="HTML", disable_notification=disable_notif, disable_web_page_preview=True)
                elif "photo_file_id" in data:
                    await bot.send_photo(chat_id, data["photo_file_id"], caption=data.get("caption", "") + sig_text, parse_mode="HTML", disable_notification=disable_notif)
                elif "video_file_id" in data:
                    await bot.send_video(chat_id, data["video_file_id"], caption=data.get("caption", "") + sig_text, parse_mode="HTML", disable_notification=disable_notif)

            elif platform == "facebook":
                from utils.telethon_client import client as telethon_client
                post_data = {}

                if "text" in data:
                    post_data["text"] = data["text"]
                elif "photo_file_id" in data:
                    post_data["media_type"] = "photo"
                    post_data["message_id"] = data["photo_file_id"]
                    post_data["from_chat_id"] = chat_id
                    post_data["text"] = data.get("caption", "")
                elif "video_file_id" in data:
                    post_data["media_type"] = "video"
                    post_data["message_id"] = data["video_file_id"]
                    post_data["from_chat_id"] = chat_id
                    post_data["text"] = data.get("caption", "")

                if post_data:
                    ok = await publish_to_facebook(post_data, chat_id, telethon_client)
                    if not ok:
                        raise Exception("publish_to_facebook повернув False")
                else:
                    raise Exception("Немає контенту для публікації")

        except Exception as e:
            logging.error(f"❌ Не вдалося надіслати до {title} ({platform}): {e}")
            failed.append(title)

    await state.clear()
    ok = len(targets) - len(failed)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Опублікувати ще", callback_data="publish_news")],
        [InlineKeyboardButton(text="🏠 Головне меню", callback_data="back_main")]
    ])

    if ok == 0:
        await callback.message.edit_text("❗️ Не вдалося опублікувати жодного разу.", reply_markup=kb)
    elif not failed:
        await callback.message.edit_text(f"✅ Опубліковано в {ok} медіа.", reply_markup=kb)
    else:
        await callback.message.edit_text(f"⚠️ Опубліковано: {ok} | Не вдалося: {', '.join(failed)}", reply_markup=kb)
