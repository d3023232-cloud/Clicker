"""Управление данными пользователей"""
import json
import os
import time
from collections import defaultdict
import config

# Глобальные данные
user_data = defaultdict(lambda: {
    "clicks": 0,
    "coins": 0,
    "click_power": 1.0,
    "auto_clicker": 0.0,
    "last_click": time.time(),
    "last_daily": 0,
    "achievements": set(),
    "title": "Новичок",
    "league": "🥉 Бронзовая",
    "premium": False,
    "premium_until": 0,
    "donate_coins": 0,
    "referrer_id": None,
    "last_reminder": 0,
    "reminders_enabled": True
})

user_names = {}

def save_data():
    """Сохраняет данные в JSON файл"""
    try:
        serializable_user_data = {}
        for uid, data in user_data.items():
            serializable_user_data[str(uid)] = {
                "clicks": data["clicks"],
                "coins": data["coins"],
                "click_power": data["click_power"],
                "auto_clicker": data["auto_clicker"],
                "last_click": data["last_click"],
                "last_daily": data["last_daily"],
                "achievements": list(data["achievements"]),
                "title": data["title"],
                "league": data["league"],
                "premium": data["premium"],
                "premium_until": data["premium_until"],
                "donate_coins": data["donate_coins"],
                "referrer_id": data["referrer_id"],
                "last_reminder": data["last_reminder"],
                "reminders_enabled": data["reminders_enabled"]
            }

        with open(config.DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "user_data": serializable_user_data,
                "user_names": user_names
            }, f, ensure_ascii=False, indent=2)
        print("💾 Данные сохранены.")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        return False

def load_data():
    """Загружает данные из JSON файла"""
    global user_data, user_names
    if not os.path.exists(config.DATA_FILE):
        print("📁 Файл данных не найден. Создаётся новый.")
        return

    try:
        with open(config.DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        loaded_user_data = data.get("user_data", {})
        for uid_str, ud in loaded_user_data.items():
            uid = int(uid_str)
            user_data[uid] = {
                "clicks": ud.get("clicks", 0),
                "coins": ud.get("coins", 0),
                "click_power": ud.get("click_power", 1.0),
                "auto_clicker": ud.get("auto_clicker", 0.0),
                "last_click": ud.get("last_click", time.time()),
                "last_daily": ud.get("last_daily", 0),
                "achievements": set(ud.get("achievements", [])),
                "title": ud.get("title", "Новичок"),
                "league": ud.get("league", "🥉 Бронзовая"),
                "premium": ud.get("premium", False),
                "premium_until": ud.get("premium_until", 0),
                "donate_coins": ud.get("donate_coins", 0),
                "referrer_id": ud.get("referrer_id"),
                "last_reminder": ud.get("last_reminder", 0),
                "reminders_enabled": ud.get("reminders_enabled", True)
            }

        user_names.update(data.get("user_names", {}))
        print(f"✅ Загружено {len(user_data)} игроков из файла.")
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")

def get_user_data(user_id):
    """Получает данные пользователя"""
    return user_data[user_id]

def update_user_name(user_id, name):
    """Обновляет имя пользователя"""
    user_names[user_id] = name

def get_user_name_by_id(user_id):
    """Получает имя пользователя по ID"""
    return user_names.get(user_id, f"ID{user_id}")

def reset_user_data(user_id):
    """Сбрасывает данные пользователя"""
    user_data[user_id] = {
        "clicks": 0,
        "coins": 0,
        "click_power": 1.0,
        "auto_clicker": 0.0,
        "last_click": time.time(),
        "last_daily": 0,
        "achievements": set(),
        "title": "Новичок",
        "league": "🥉 Бронзовая",
        "premium": False,
        "premium_until": 0,
        "donate_coins": 0,
        "referrer_id": None,
        "last_reminder": 0,
        "reminders_enabled": True
    }
    save_data()
