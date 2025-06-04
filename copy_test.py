from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import os
from dotenv import load_dotenv

load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION = os.getenv("TELETHON_SESSION")

client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

with client:
    for dialog in client.iter_dialogs():
        if dialog.is_channel:
            print(f"{dialog.name}: {dialog.id}")
