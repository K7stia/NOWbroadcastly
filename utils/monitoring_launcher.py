import html
import logging
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from aiogram.fsm.context import FSMContext
from aiogram import Bot

from utils.json_storage import (
    load_groups,
    load_config,
    load_monitoring_groups,
    load_media,
    get_source_signature
)
from utils.monitoring_utils import build_channels_with_id, filter_posts_by_stop_words, build_full_caption
from utils.telethon_fetcher import forward_post_to_staging, fetch_posts_for_category
from utils.rewrite import rewrite_text
from routers.monitoring_moderation import send_post_to_moderation
from utils.facebook_publisher import publish_to_facebook
from utils.instagram_publisher import publish_to_instagram

from utils.monitoring_core import build_channels_with_id, build_full_caption, filter_posts_by_stop_words

async def manual_monitor_launch(callback: CallbackQuery, state: FSMContext, bot: Bot):
    logging.debug("✅ manual_monitor_launch TRIGGERED")

    data = await state.get_data()
    logging.debug(f"✅ FSM DATA: {data}")
    await state.clear()

    category = data.get('category')
    if not category:
        monitoring_groups = data.get("monitoring_groups", [])
        if monitoring_groups:
            category = monitoring_groups[0]
            logging.debug(f"[category fallback] Використано першу групу як категорію: {category}")
        else:
            category = None

    model = data.get('model') or data.get('monitoring_model')
    data["monitoring_model"] = model
    moderation = data.get('moderation', False)
    rewrite = data.get('rewrite', False)
    skip_forwards = data.get('skip_forwards', True)

    if not category or not model:
        await callback.message.edit_text("❗️Помилка: відсутні необхідні дані для запуску моніторингу.")
        return

    groups_data = load_groups()
    media_list = load_media()
    media_targets = build_channels_with_id(data, media_list, groups_data)
    logging.warning(f"[debug-media-targets] {media_targets}")

    if not media_targets:
        logging.error(f"[‼️] Немає цілей для публікації. Перевір media.json або структуру сценарію.")
        await callback.message.edit_text("❌ Не обрано жодного медіа або групи для публікації.")
        return

    sources = load_monitoring_groups().get(category, {}).get('channels', [])
    posts = await fetch_posts_for_category(sources, skip_forwards=skip_forwards)

    all_filtered = []
    for channel in sources:
        chan_id = channel.get("id")
        channel_posts = [p for p in posts if p.get("channel_id") == chan_id]
        filtered = filter_posts_by_stop_words(channel_posts, chan_id)
        all_filtered.extend(filtered)

    posts = all_filtered

    if not posts:
        await callback.message.edit_text(
            "❌ Усі публікації містили стоп-слова/репости або не містили контенту для публікації.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Спробувати ще", callback_data="manual_monitoring")],
                [InlineKeyboardButton(text="🏠 На головну", callback_data="back_main")]
            ])
        )
        return

    top = posts[0]
    top["category"] = category
    top = await forward_post_to_staging(top)
    logging.warning(f"[debug-top-after-forward] {top}")

    if not top:
        await callback.message.edit_text("❌ Помилка при пересиланні поста.")
        return

    if not top.get("html_text") and top.get("text"):
        top["html_text"] = top["text"]

    if not top.get("html_text"):
        await callback.message.edit_text("❌ Не вдалося отримати текст з поста.")
        return

    if rewrite:
        style = load_config().get("rewrite_style", "Перефразуй цей текст для Telegram-каналу")
        top["html_text"] = await rewrite_text(top["html_text"], style)
        if top["html_text"].startswith("[❗️Помилка рерайту"):
            await callback.message.edit_text("❌ Помилка рерайту. Моніторинг скасовано.")
            return

    source_sig = get_source_signature(category, top.get("from_chat_id"))
    if source_sig:
        top["html_text"] = f'{top["html_text"].strip()}\n\n{source_sig}'

    if moderation:
        await send_post_to_moderation(bot, top, "(група/медіа)", category, model)
        await callback.message.edit_text("📨 Пост надіслано на модерацію")
        return

    successful = []
    failed = []

    for media in media_targets:
        chat_id = media["id"]
        title = media.get("title") or str(chat_id)
        platform = media.get("platform", "telegram")
        try:
            caption = build_full_caption(top["html_text"], chat_id, platform=platform)
            media_type = top.get("media_type", "text")

            if platform == "telegram":
                if media_type == "text":
                    await bot.send_message(chat_id=chat_id, text=caption, parse_mode="HTML")

                elif media_type in ["photo", "video"]:
                    file_obj = top.get("file_object")
                    if not file_obj:
                        raise Exception("❌ Немає file_object для медіа")

                    if media_type == "photo":
                        await bot.send_photo(chat_id=chat_id, photo=file_obj, caption=caption, parse_mode="HTML")
                    elif media_type == "video":
                        await bot.send_video(chat_id=chat_id, video=file_obj, caption=caption, parse_mode="HTML")

                elif media_type == "album":
                    album = []
                    added_caption = False
                    for m in top.get("media_group", [])[:10]:
                        file_obj = m.get("file_object")
                        if not file_obj:
                            continue

                        media_item = None
                        if m["type"] in ["photo", "messagemediaphoto", "mediaphoto"]:
                            media_item = InputMediaPhoto(media=file_obj)
                        elif m["type"] in ["video", "messagemediavideo", "mediavideo"]:
                            media_item = InputMediaVideo(media=file_obj)

                        if media_item:
                            if not added_caption:
                                media_item.caption = caption
                                media_item.parse_mode = "HTML"
                                added_caption = True
                            album.append(media_item)

                    if album:
                        await bot.send_media_group(chat_id, media=album)
                    else:
                        raise Exception("❌ Не вдалося зібрати album з file_object")

            elif platform == "facebook":
                client = getattr(bot, "client", None)
                result = await publish_to_facebook(post=top, page_id=chat_id, client=client)
                if result is not True:
                    raise Exception(result or "❌ Публікація у Facebook завершилась помилкою")

            elif platform == "instagram":
                client = getattr(bot, "client", None)
                result = await publish_to_instagram(post=top, page_id=chat_id, client=client)
                if result is not True:
                    raise Exception(result or "❌ Публікація в Instagram завершилась помилкою")

            successful.append(media)

        except Exception as e:
            logging.error(f"❌ Не вдалося опублікувати до {title} ({platform}): {e}")
            media["error"] = str(e).strip().split("\n")[-1]
            failed.append(media)

    summary_lines = [
        "✅ <b>Моніторинг завершено</b>",
        "",
        f"<b>Категорія:</b> <code>{category}</code>",
        f"<b>Модель:</b> <code>{model}</code>",
        f"<b>Опції:</b> "
        f"{'✅ Модерація' if moderation else '🚫 Без модерації'}, "
        f"{'✅ Рерайт' if rewrite else '🚫 Без рерайту'}, "
        f"{'✅ Пропуск репостів' if skip_forwards else '🚫 Без пропуску репостів'}",
        ""
    ]

    top_preview = top.get("text", "") or top.get("html_text", "")
    summary_lines.append("\n🔍 <b>Публікація з моніторингу:</b>\n" + html.escape(top_preview)[:120] + "..." if top_preview else "–")

    if successful:
        summary_lines.append(f"\n<b>Успішно: {len(successful)}</b> ⬇️")
        for item in successful:
            title = item.get("title") or str(item.get("id"))
            platform = item.get("platform", "telegram")
            summary_lines.append(f"– {title} ({platform})")

    if failed:
        summary_lines.append(f"\n<b>Помилки: {len(failed)}</b> ⬇️")
        for item in failed:
            title = item.get("title") or str(item.get("id"))
            platform = item.get("platform", "telegram")
            err_msg = item.get("error", "Невідома помилка")
            summary_lines.append(f"– {title} ({platform})\n<code>{err_msg}</code>")
    else:
        summary_lines.append("\n<b>Помилки: 0</b>")

    try:
        await callback.message.answer(
            "\n".join(summary_lines),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📡 Запустити ще раз", callback_data="manual_monitoring")],
                [InlineKeyboardButton(text="🏠 На головну", callback_data="back_main")]
            ])
        )
    except Exception as e:
        logging.error(f"[manual_monitor_launch] ❌ Не вдалося надіслати відповідь користувачу: {e}")
