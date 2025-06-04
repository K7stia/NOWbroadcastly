import json
import logging
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
STORAGE_DIR = BASE_DIR / "storage"

GROUPS_FILE = STORAGE_DIR / "groups.json"
CONFIG_FILE = STORAGE_DIR / "config.json"
SIGNATURES_FILE = STORAGE_DIR / "channel_signature.json"
MONITORING_GROUPS_PATH = STORAGE_DIR / "monitoring_groups.json"
MEDIA_FILE = STORAGE_DIR / "media.json"
SCENARIOS_FILE = STORAGE_DIR / "scenarios.json"

# === Ініціалізація ===
if not STORAGE_DIR.exists():
    STORAGE_DIR.mkdir()

for path, default in [
    (GROUPS_FILE, {}),
    (CONFIG_FILE, {"signature": ""}),
    (SIGNATURES_FILE, {}),
    (MONITORING_GROUPS_PATH, {}),
    (MEDIA_FILE, {}),
]:
    if not path.exists():
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)

# === GROUPS ===
def load_groups() -> dict:
    try:
        with open(GROUPS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}

def save_groups(data: dict) -> None:
    with open(GROUPS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# === CONFIG ===
def load_config() -> dict:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {"signature": ""}
    except json.JSONDecodeError:
        return {"signature": ""}

def save_config(data: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# === SIGNATURES ===
def load_channel_signature(channel_id: int | str) -> dict:
    if SIGNATURES_FILE.exists():
        with open(SIGNATURES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get(str(channel_id), {})
    return {}

def save_channel_signature(channel_id: int | str, signature: str, enabled: bool = True) -> None:
    data = {}
    if SIGNATURES_FILE.exists():
        with open(SIGNATURES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    data[str(channel_id)] = {"signature": signature, "enabled": enabled}
    with open(SIGNATURES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def delete_channel_signature(channel_id: int | str) -> None:
    if not SIGNATURES_FILE.exists():
        return
    with open(SIGNATURES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.pop(str(channel_id), None)
    with open(SIGNATURES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# === MONITORING GROUPS ===
def load_monitoring_groups() -> dict:
    try:
        with open(MONITORING_GROUPS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_monitoring_groups(data: dict):
    with open(MONITORING_GROUPS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# === MEDIA ===
def load_media() -> dict:
    if MEDIA_FILE.exists():
        with open(MEDIA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_media(data: dict) -> None:
    with open(MEDIA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_known_media() -> dict:
    """
    Повертає медіа, які або:
    - не телеграм (тобто фейсбук), або
    - телеграм і мають known=true
    """
    if not MEDIA_FILE.exists():
        return {}

    with open(MEDIA_FILE, "r", encoding="utf-8") as f:
        media = json.load(f)

    return {
        key: val for key, val in media.items()
        if val.get("platform") != "telegram" or val.get("known") is True
    }

# === TRIM SETTINGS ===
def get_trim_settings(category: str, channel_id: int) -> dict:
    groups = load_monitoring_groups()
    channels = groups.get(category, {}).get("channels", [])
    for ch in channels:
        if ch.get("id") == channel_id:
            settings = {
                "lines_to_trim": ch.get("lines_to_trim", 0),
                "trim_phrases": ch.get("trim_phrases", [])
            }
            logging.debug(f"[get_trim_settings] ✅ Found settings for channel {channel_id}: {settings}")
            return settings
    logging.debug(f"[get_trim_settings] ⛔️ No settings found for channel {channel_id}")
    return {"lines_to_trim": 0, "trim_phrases": []}

def update_trim_settings(category: str, channel_id: int, lines_to_trim: int = None, trim_phrases: list = None):
    groups = load_monitoring_groups()
    channels = groups.get(category, {}).get("channels", [])
    for ch in channels:
        if ch.get("id") == channel_id:
            if lines_to_trim is not None:
                ch["lines_to_trim"] = lines_to_trim
            if trim_phrases is not None and isinstance(trim_phrases, list):
                ch["trim_phrases"] = trim_phrases
            save_monitoring_groups(groups)
            logging.debug(f"[update_trim_settings] 💾 Updated settings for channel {channel_id}")
            return
    logging.warning(f"[update_trim_settings] ⚠️ Channel {channel_id} not found in category '{category}'")

def get_source_signature(category: str, channel_id: int) -> str | None:
    groups = load_monitoring_groups()
    for ch in groups.get(category, {}).get("channels", []):
        if ch.get("id") == channel_id:
            sig_data = ch.get("source_signature", {})
            if isinstance(sig_data, dict) and sig_data.get("enabled") and sig_data.get("text"):
                return sig_data["text"].strip()
    return None

def update_source_signature(category: str, channel_id: int, text: str, enabled: bool = True):
    groups = load_monitoring_groups()
    for ch in groups.get(category, {}).get("channels", []):
        if ch.get("id") == channel_id:
            ch["source_signature"] = {"enabled": enabled, "text": text}
            break
    save_monitoring_groups(groups)

def delete_source_signature(category: str, channel_id: int):
    groups = load_monitoring_groups()
    for ch in groups.get(category, {}).get("channels", []):
        if ch.get("id") == channel_id and "source_signature" in ch:
            del ch["source_signature"]
            break
    save_monitoring_groups(groups)

def get_stop_words(category: str, channel_id: int) -> list:
    groups = load_monitoring_groups()
    for ch in groups.get(category, {}).get("channels", []):
        if ch.get("id") == channel_id:
            return ch.get("stop_words", [])
    return []

def update_stop_words(category: str, channel_id: int, words: list):
    groups = load_monitoring_groups()
    for ch in groups.get(category, {}).get("channels", []):
        if ch.get("id") == channel_id:
            ch["stop_words"] = words
            break
    save_monitoring_groups(groups)

def delete_stop_words(category: str, channel_id: int):
    groups = load_monitoring_groups()
    for ch in groups.get(category, {}).get("channels", []):
        if ch.get("id") == channel_id and "stop_words" in ch:
            del ch["stop_words"]
            break
    save_monitoring_groups(groups)

# Ініціалізація
if not SCENARIOS_FILE.exists():
    with open(SCENARIOS_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, indent=2, ensure_ascii=False)

# === SCENARIOS ===
def load_scenarios() -> dict:
    try:
        with open(SCENARIOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_scenarios(data: dict):
    for k, v in data.items():
        if "active" not in v:
            v["active"] = False
    with open(SCENARIOS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 🧠 Автоматичне оновлення планувальника
    try:
        from utils.scheduler import reload_scheduler
        reload_scheduler()
    except Exception as e:
        logging.warning(f"[save_scenarios] ⚠️ Failed to reload scheduler: {e}")
