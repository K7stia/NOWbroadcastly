import re
import logging
from html import escape
from bs4 import BeautifulSoup
from utils.json_storage import load_groups, load_known_media, load_channel_signature, load_monitoring_groups

from utils.monitoring_core import build_channels_with_id, build_full_caption, filter_posts_by_stop_words
from utils.monitoring_launcher import manual_monitor_launch
from aiogram.types import CallbackQuery
from types import SimpleNamespace

def fix_malformed_links(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    anchors = soup.find_all('a')

    for a in anchors:
        prev = a.previous_sibling
        if prev and isinstance(prev, str) and prev.strip() and not prev.strip().startswith("<"):
            a.string = (prev.strip() + " " + (a.string or "")).strip()
            prev.extract()

        nxt = a.next_sibling
        if nxt and isinstance(nxt, str) and nxt.strip() and not nxt.strip().startswith("<"):
            a.string = ((a.string or "") + " " + nxt.strip()).strip()
            nxt.extract()

    return str(soup)

def custom_html_formatter(text: str) -> str:
    platforms = {
        "ТЕЛЕГРАМ": r"(📩)?(ТЕЛЕГРАМ)",
        "ТІКТОК": r"(🔓)?(ТІКТОК)",
        "ФЕЙСБУК": r"(😎)?(ФЕЙСБУК)",
    }

    urls = re.findall(r'https?://\S+', text)
    if not urls:
        return text

    url_index = 0
    for name, pattern in platforms.items():
        match = re.search(pattern, text)
        if match and url_index < len(urls):
            emoji = match.group(1) or ""
            label = match.group(2)
            url = urls[url_index]
            url_index += 1

            link_html = f'{emoji}<a href="{escape(url)}">{escape(label)}</a>'
            text = text.replace(match.group(0), link_html, 1)

    text = re.sub(r'https?://\S+', '', text)
    return text


def contains_stop_words(text: str, stop_words: list[str]) -> bool:
    text_lower = text.lower()
    for word in stop_words:
        if word.lower() in text_lower:
            return True
    return False


async def run_monitoring_scenario(name: str):
    from utils.json_storage import load_scenarios

    scenarios = load_scenarios()
    scenario = scenarios.get(name)

    if not scenario:
        logging.warning(f"[run_monitoring_scenario] ❌ Сценарій '{name}' не знайдено.")
        return

    data = {
        "selected_groups": scenario.get("monitoring_groups", []),
        "selected_channels": [],  # ми працюємо через групи
        "targets": scenario.get("targets", []),
        "moderation": scenario.get("moderation", False),
        "rewrite": scenario.get("rewrite", False),
        "skip_forwards": scenario.get("skip_forwards", True),
        "scenario_name": name
    }

    logging.info(f"[run_monitoring_scenario] ▶️ Запускаємо сценарій '{name}' з {len(data['selected_groups'])} групами")
    await manual_monitor_launch(data)

async def launch_monitoring_from_dict(data: dict, callback, bot):
    class FakeState:
        async def get_data(self):
            return data

        async def clear(self):
            pass

    await manual_monitor_launch(callback, state=FakeState(), bot=bot)
