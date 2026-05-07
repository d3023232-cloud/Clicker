"""Мини-игры: Краш, Рулетка, Дуэль"""
import random
import asyncio
import config
import data_manager
from game_logic import update_league
from utils import format_number, generate_crash_multiplier

def validate_bet(user_id, bet_text, min_bet, max_bet):
    """Валидация ставки"""
    try:
        bet = int(bet_text)
        if bet < min_bet:
            return {"success": False, "message": f"❌ Минимальная ставка: {min_bet} монет."}
        if bet > max_bet:
            return {"success": False, "message": f"❌ Максимальная ставка: {max_bet} монет."}
        if data_manager.user_data[user_id]["coins"] < bet:
            return {"success": False, "message": "❌ Недостаточно монет!"}
        return {"success": True, "bet": bet}
    except ValueError:
        return {"success": False, "message": "❌ Введите целое число (например: 100)"}

# === КРАШ ===
def start_crash_game(user_id):
    """Начинает игру Краш"""
    if data_manager.user_data[user_id]["coins"] < config.MIN_BET:
        return {"success": False, "message": "❌ Нужно минимум 20 монет!"}
    return {"success": True}

def process_crash_game(user_id, bet, multiplier):
    """Обрабатывает игру Краш"""
    ud = data_manager.user_data[user_id]

    if ud["coins"] < bet:
        return {"success": False, "message": "❌ Недостаточно монет!"}

    bot_multiplier = generate_crash_multiplier()

    if bot_multiplier >= multiplier:
        win = int(bet * multiplier)
        ud["coins"] += win
        update_league(user_id)
        data_manager.save_data()
        return {
            "success": True,
            "win": True,
            "message": (
                f"✅ <b>УСПЕХ!</b>
"
                f"Ваш множитель: {multiplier}x
"
                f"Взрыв: {bot_multiplier}x
"
                f"Вы выиграли: <b>+{format_number(win)}</b> монет! 🎉"
            ),
            "bot_multiplier": bot_multiplier
        }
    else:
        ud["coins"] -= bet
        update_league(user_id)
        data_manager.save_data()
        return {
            "success": True,
            "win": False,
            "message": (
                f"💥 <b>ВЗРЫВ!</b>
"
                f"Ваш множитель: {multiplier}x
"
                f"Взрыв: {bot_multiplier}x
"
                f"Вы потеряли: <b>{format_number(bet)}</b> монет 😢"
            ),
            "bot_multiplier": bot_multiplier
        }

# === РУЛЕТКА ===
def start_roulette_game(user_id):
    """Начинает игру Рулетка"""
    if data_manager.user_data[user_id]["coins"] < config.MIN_BET:
        return {"success": False, "message": "❌ Нужно минимум 20 монет!"}
    return {"success": True}

def process_roulette_game(user_id, bet, color):
    """Обрабатывает игру Рулетка"""
    ud = data_manager.user_data[user_id]

    if ud["coins"] < bet:
        return {"success": False, "message": "❌ Недостаточно монет!"}

    rand = random.random()
    if rand < 0.45:
        result = "red"
    elif rand < 0.90:
        result = "black"
    else:
        result = "green"

    win = 0
    if color == result:
        if color == "green":
            win = int(bet * 9.0)
        else:
            win = int(bet * 1.9)
        ud["coins"] += win
        message = f"✅ Выпало {result}! Вы выиграли <b>+{format_number(win)}</b> монет!"
    else:
        ud["coins"] -= bet
        message = f"❌ Выпало {result}. Вы потеряли <b>{format_number(bet)}</b> монет."

    update_league(user_id)
    data_manager.save_data()

    return {
        "success": True,
        "win": color == result,
        "message": message,
        "result": result,
        "balance": ud["coins"]
    }

# === ДУЭЛЬ ===
def start_duel_game(user_id):
    """Начинает игру Дуэль"""
    if data_manager.user_data[user_id]["coins"] < config.MIN_DUEL_BET:
        return {"success": False, "message": "❌ Нужно минимум 100 монет!"}
    return {"success": True}

def process_duel_game(user_id, bet):
    """Обрабатывает игру Дуэль"""
    ud = data_manager.user_data[user_id]

    if ud["coins"] < bet:
        return {"success": False, "message": "❌ Недостаточно монет!"}

    if random.random() < 0.48:
        win = int(bet * 0.96)
        ud["coins"] += win
        message = f"✅ Вы победили! Получено <b>+{format_number(win)}</b> монет (с учётом комиссии)."
    else:
        ud["coins"] -= bet
        message = f"❌ Вы проиграли <b>{format_number(bet)}</b> монет."

    update_league(user_id)
    data_manager.save_data()

    return {
        "success": True,
        "message": message,
        "balance": ud["coins"]
    }
