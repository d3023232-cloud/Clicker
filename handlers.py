"""Фоновые напоминания пользователям"""
import time
import random
import config
import data_manager

async def send_reminders(context):
    """Отправляет напоминания неактивным пользователям"""
    now = time.time()
    for user_id, ud in list(data_manager.user_data.items()):
        if not ud.get("reminders_enabled", True):
            continue

        last = ud.get("last_reminder", 0)
        if now - last >= random.randint(config.REMINDER_INTERVAL_MIN, config.REMINDER_INTERVAL_MAX):
            try:
                msg = random.choice(config.REMINDER_MESSAGES)
                await context.bot.send_message(chat_id=user_id, text=f"🔔 {msg}")
                data_manager.user_data[user_id]["last_reminder"] = now
                data_manager.save_data()
            except Exception:
                pass
