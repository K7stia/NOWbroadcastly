from utils.telethon_fetcher import fetch_posts_for_category
from datetime import datetime, timezone
import logging

# 🔧 Лог-файл
logging.basicConfig(
    level=logging.INFO,
    filename="monitoring_scores.log",
    filemode="a",
    encoding="utf-8",
    format="%(asctime)s - %(message)s"
)

def ensure_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    return datetime.now(timezone.utc)

def calc_score(p, publish_mode="unknown"):
    views = p.get("views", 0)
    forwards = p.get("forwards", 0)
    subs = max(p.get("subscribers", 1), 1)

    post_date = ensure_datetime(p.get("date"))
    now = datetime.now(timezone.utc)

    age_minutes = (now - post_date).total_seconds() / 60
    age_hours = age_minutes / 60

    if age_hours > 12:
        return 0

    base_score = (views + forwards * 10) / subs

    if age_minutes <= 30:
        multiplier = 1.8
    elif age_minutes <= 60:
        multiplier = 1.5
    elif age_hours <= 2:
        multiplier = 1.2
    elif age_hours <= 6:
        multiplier = 1.0
    else:
        multiplier = 0.7

    final_score = base_score * multiplier

    if final_score > 0:
        preview = (p.get("html_text") or p.get("text") or "").strip()[:50].replace('\n', ' ')
        source = p.get("channel") or "unknown"
        msg_id = p.get("original_msg_id") or p.get("original_group_ids", ["?"])[0]

        logging.info(
            f"[{source}] → {publish_mode.upper()} | MsgID: {msg_id} | Score: {final_score:.4f} | Views: {views} | "
            f"Forwards: {forwards} | Subs: {subs} | Age(h): {age_hours:.2f} | Multiplier: {multiplier} | Text: \"{preview}\""
        )

    return final_score

async def get_posts(sources: list, publish_mode="unknown") -> list:
    posts = await fetch_posts_for_category(sources)
    return sorted(posts, key=lambda p: calc_score(p, publish_mode), reverse=True)
