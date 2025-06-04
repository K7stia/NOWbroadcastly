import logging
import html
import re

from utils.json_storage import (
    load_config,
    get_source_signature,
    get_stop_words,
    load_media,
    load_groups,
    load_channel_signature
)

def build_channels_with_id(data, known_media, groups_data):
    all_ids = set()

    # ✅ targets (використовується в сценаріях)
    for item in data.get("targets", []):
        if isinstance(item, dict) and "id" in item:
            all_ids.add(item["id"])

    # ✅ selected_channels (використовується у FSM)
    for ch in data.get("selected_channels", []):
        if isinstance(ch, int):
            all_ids.add(ch)
        elif isinstance(ch, str):
            try:
                all_ids.add(int(ch))
            except ValueError:
                # можливо, це username або title — спробуємо знайти в known_media
                for v in known_media.values():
                    if ch == v.get("title") or ch == v.get("username"):
                        all_ids.add(v["id"])

    # ✅ selected_groups (додає канали з груп — теж FSM)
    for group in data.get("selected_groups", []):
        for ch in groups_data.get(group, []):
            if isinstance(ch, dict) and "id" in ch:
                all_ids.add(ch["id"])
            elif isinstance(ch, int):
                all_ids.add(ch)

    result = []
    for ch_id in all_ids:
        info = known_media.get(str(ch_id))  # ключі в media.json — рядки
        if info and "id" in info:
            result.append({
                "id": info["id"],
                "title": info.get("title", f"{ch_id}"),
                "platform": info.get("platform", "telegram")
            })

    return result


def build_full_caption(text: str, chat_id: int, remove_links: bool = False, platform: str = "telegram") -> str:
    logging.debug(f"[build_full_caption] ▶️ chat_id={chat_id}, remove_links={remove_links}, platform={platform}")

    caption = text or ""

    if remove_links:
        logging.debug("[build_full_caption] ⚠️ Форматування лінків вимкнене — лінки не обробляються")

    # Додаємо підпис ТІЛЬКИ ДЛЯ TELEGRAM
    if platform == "telegram":
        sig_info = load_channel_signature(chat_id)
        raw_sig = sig_info.get("signature", "")
        if sig_info.get("enabled", True) and raw_sig:
            logging.debug(f"[build_full_caption] 🖋 Додаємо підпис (довжина {len(raw_sig)} симв.)")
            caption += "\n\n" + raw_sig
        else:
            logging.debug("[build_full_caption] ℹ️ Підпис вимкнено або порожній")
    else:
        logging.debug("[build_full_caption] 🚫 Підпис не додається — не Telegram")

    logging.debug(f"[build_full_caption] 🧾 Фінальний текст (обрізано): {caption[:100]}...")
    return caption.strip()

def filter_posts_by_stop_words(posts: list, chat_id: int) -> list:
    from utils.json_storage import load_monitoring_groups

    monitoring_groups = load_monitoring_groups()
    stop_words = []

    # знайти категорію, якій відповідає цей chat_id
    for group_name, group_data in monitoring_groups.items():
        for ch in group_data.get("channels", []):
            if ch.get("id") == chat_id:
                stop_words = ch.get("stop_words", [])
                break

    if not stop_words:
        return posts  # немає стоп-слів — нічого не фільтруємо

    filtered = []
    for p in posts:
        text = p.get("text", "") or ""
        text_lc = text.lower()
        matched = False
        for phrase in stop_words:
            if phrase.lower() in text_lc:
                print(f"[STOP WORDS] 🚫 Збіг по стоп-слову: '{phrase}' → {text[:60]}...")
                matched = True
                break
        if not matched:
            filtered.append(p)

    print(f"[STOP WORDS] 🔎 Всього: {len(posts)} → Пройшло: {len(filtered)}")

    return filtered
