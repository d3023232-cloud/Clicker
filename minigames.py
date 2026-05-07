"""Вспомогательные функции"""
import time
import random
import config

def format_number(n: int) -> str:
    """Форматирует число с разделителями: 1234567 → 1,234,567"""
    return f"{int(n):,}"

def generate_crash_multiplier() -> float:
    """Генератор множителя для игры Краш"""
    r = random.random()
    if r >= 0.9999:
        return 100.0
    crash = 0.99 / (1 - r)
    return min(100.0, round(crash, 2))

def get_time_greeting():
    """Возвращает приветствие в зависимости от времени суток"""
    hour = time.localtime().tm_hour
    if 0 <= hour < 7:
        return "🌙 Сладких снов!"
    elif 7 <= hour < 12:
        return "☀️ Доброе утро!"
    elif 12 <= hour < 18:
        return "🌤 Добрый день!"
    else:
        return "🌆 Добрый вечер!"

def get_league(coins):
    """Определяет лигу пользователя по количеству монет"""
    for min_coins, name in reversed(config.LEAGUES):
        if coins >= min_coins:
            return name
    return config.LEAGUES[0][1]

def get_user_name(user):
    """Получает имя пользователя"""
    return user.full_name if user.full_name else f"ID{user.id}"

def is_premium_active(user_data):
    """Проверяет активность Premium-статуса"""
    if not user_data.get("premium", False):
        return False
    if user_data.get("premium_until", 0) == 0:
        return True  # навсегда
    return time.time() < user_data["premium_until"]
