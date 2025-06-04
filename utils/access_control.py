import json
from pathlib import Path
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

# Шлях до JSON-файлу
ALLOWED_USERS_PATH = Path(__file__).parent.parent / "storage" / "allowed_users.json"

# 🔐 Супер-адмін (його не можна видалити)
SUPER_ADMIN_ID = 264414

def load_allowed_users() -> list[int]:
    try:
        with open(ALLOWED_USERS_PATH, "r") as f:
            users = json.load(f)
            # гарантуємо, що супер-адмін завжди є в списку
            if SUPER_ADMIN_ID not in users:
                users.append(SUPER_ADMIN_ID)
            return users
    except Exception:
        return [SUPER_ADMIN_ID]

def save_allowed_users(users: list[int]):
    # гарантуємо, що супер-адмін завжди присутній
    if SUPER_ADMIN_ID not in users:
        users.append(SUPER_ADMIN_ID)
    with open(ALLOWED_USERS_PATH, "w") as f:
        json.dump(users, f)

def is_user_allowed(user_id: int) -> bool:
    return user_id in load_allowed_users()

def add_user(user_id: int):
    users = load_allowed_users()
    if user_id not in users:
        users.append(user_id)
        save_allowed_users(users)

def remove_user(user_id: int):
    if user_id == SUPER_ADMIN_ID:
        return  # не дозволяємо видалення супер-адміна
    users = load_allowed_users()
    if user_id in users:
        users.remove(user_id)
        save_allowed_users(users)

# ✅ Кастомний фільтр доступу
class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return is_user_allowed(event.from_user.id)
