"""Админ-команды и панель"""
import time
import config
import data_manager
from game_logic import update_league
from utils import format_number, is_premium_active

def is_admin(user_id):
    """Проверяет, является ли пользователь админом"""
    return user_id in config.ADMIN_IDS

def get_admin_panel_text():
    """Формирует текст админ-панели"""
    commands_list = [
        "/debug — Показать отладочную информацию",
        "/add_coins [user_id] [amount] — Добавить монет пользователю",
        "/give_donate [user_id] [amount] — Выдать Donat-коины",
        "/give_premium [user_id] [days] — Выдать Premium",
        "/get_user [user_id] — Показать данные пользователя",
        "/reset_user [user_id] — Сбросить данные пользователя",
        "/stats — Показать статистику бота",
        "/give_daily [user_id] — Сбросить ежедневный бонус",
        "/ban_user [user_id] — Заблокировать пользователя",
        "/test_achievements [user_id] — Выдать все достижения",
        "/broadcast [message] — Отправить сообщение всем",
        "/admins — Показать это меню"
    ]
    return "🔐 <b>Админ-панель</b>

" + "
".join(commands_list)

def get_admin_keyboard():
    """Формирует клавиатуру админ-панели"""
    from telegram import InlineKeyboardButton

    keyboard = [
        [InlineKeyboardButton("📋 Статистика (/stats)", callback_data="admin_cmd_stats")],
        [InlineKeyboardButton("💰 Добавить монеты (/add_coins)", callback_data="admin_cmd_add_coins")],
        [InlineKeyboardButton("💎 Выдать Donat (/give_donate)", callback_data="admin_cmd_give_donate")],
        [InlineKeyboardButton("👑 Выдать Premium (/give_premium)", callback_data="admin_cmd_give_premium")],
        [InlineKeyboardButton("👤 Инфо о пользователе (/get_user)", callback_data="admin_cmd_get_user")],
        [InlineKeyboardButton("🚫 Заблокировать (/ban_user)", callback_data="admin_cmd_ban_user")],
        [InlineKeyboardButton("📤 Рассылка (/broadcast)", callback_data="admin_cmd_broadcast")],
        [InlineKeyboardButton("🔄 Сбросить данные (/reset_user)", callback_data="admin_cmd_reset_user")],
        [InlineKeyboardButton("🔧 Отладка (/debug)", callback_data="admin_cmd_debug")]
    ]
    return keyboard

def get_admin_command_description(cmd):
    """Возвращает описание админ-команды"""
    descriptions = {
        "stats": "📊 /stats — Показать статистику бота (кол-во игроков, монет в обороте и т.д.)",
        "add_coins": "💰 /add_coins <id> <amount> — Добавить монет пользователю (например: /add_coins 123456789 1000)",
        "give_donate": "💎 /give_donate <id> <amount> — Выдать Donat-коины пользователю (например: /give_donate 123456789 50)",
        "give_premium": "👑 /give_premium <id> <days> — Выдать Premium на N дней (0 = навсегда)",
        "get_user": "👤 /get_user <id> — Показать полную информацию о пользователе",
        "ban_user": "🚫 /ban_user <id> — Заблокировать пользователя (обнулить автокликер, ежедневный бонус)",
        "broadcast": "📤 /broadcast <message> — Отправить сообщение всем активным пользователям",
        "reset_user": "🔄 /reset_user <id> — Сбросить все данные пользователя",
        "debug": "🔧 /debug — Показать отладочную информацию о себе (для админов)"
    }
    return descriptions.get(cmd, "Команда не найдена.")

def add_coins(target_id, amount):
    """Добавляет монеты пользователю"""
    try:
        target_id = int(target_id)
        amount = int(amount)
        if amount <= 0:
            return {"success": False, "message": "❌ Сумма должна быть положительной"}

        data_manager.user_data[target_id]["coins"] += amount
        update_league(target_id)
        data_manager.save_data()
        return {"success": True, "message": f"✅ Добавлено {format_number(amount)} монет пользователю {target_id}."}
    except ValueError:
        return {"success": False, "message": "❌ Ошибка: ID и сумма должны быть числами."}

def give_donate(target_id, amount):
    """Выдаёт Donat-коины"""
    try:
        target_id = int(target_id)
        amount = int(amount)
        if amount <= 0:
            return {"success": False, "message": "❌ Сумма должна быть положительной"}

        data_manager.user_data[target_id]["donate_coins"] += amount
        data_manager.save_data()
        return {"success": True, "message": f"✅ Выдано {amount} Donat-коинов пользователю {target_id}."}
    except ValueError:
        return {"success": False, "message": "❌ Ошибка: ID и сумма должны быть числами."}

def give_premium(target_id, days):
    """Выдаёт Premium-статус"""
    try:
        target_id = int(target_id)
        days = int(days)

        if days == 0:
            data_manager.user_data[target_id]["premium"] = True
            data_manager.user_data[target_id]["premium_until"] = 0  # навсегда
        else:
            data_manager.user_data[target_id]["premium"] = True
            data_manager.user_data[target_id]["premium_until"] = time.time() + days * 86400

        data_manager.save_data()
        return {"success": True, "message": f"✅ Premium выдан пользователю {target_id} на {days} дней."}
    except ValueError:
        return {"success": False, "message": "❌ Ошибка: ID и дни должны быть числами."}

def get_user_info(uid):
    """Получает информацию о пользователе"""
    try:
        uid = int(uid)
        ud = data_manager.user_data[uid]
        name = data_manager.get_user_name_by_id(uid)

        msg = (
            f"👤 Пользователь: {name} (ID: {uid})
"
            f"🪙 Монет: {format_number(int(ud['coins']))}
"
            f"💎 Donat-коины: {ud['donate_coins']}
"
            f"🖱 Кликов: {format_number(ud['clicks'])}
"
            f"⚡ Сила клика: {ud['click_power']}
"
            f"🤖 Автокликер: {ud['auto_clicker']} монет/мин
"
            f"🏅 Лига: {ud['league']}
"
            f"👑 Звание: {ud['title']}
"
            f"💎 Premium: {'Да' if is_premium_active(ud) else 'Нет'}
"
            f"🎯 Достижения: {', '.join(config.ACHIEVEMENTS.get(k, {}).get('name', k) for k in ud['achievements']) or '—'}"
        )
        return {"success": True, "message": msg}
    except Exception as e:
        return {"success": False, "message": f"❌ Ошибка: {e}"}

def reset_user(uid):
    """Сбрасывает данные пользователя"""
    try:
        uid = int(uid)
        data_manager.reset_user_data(uid)
        return {"success": True, "message": f"✅ Данные пользователя {uid} сброшены."}
    except Exception as e:
        return {"success": False, "message": f"❌ Ошибка: {e}"}

def get_stats():
    """Получает статистику бота"""
    total_players = len([u for u in data_manager.user_data if data_manager.user_data[u]["coins"] > 0 or data_manager.user_data[u]["clicks"] > 0])
    total_coins = sum(u["coins"] for u in data_manager.user_data.values())
    total_donate = sum(u["donate_coins"] for u in data_manager.user_data.values())

    top_list = [(uid, data["coins"]) for uid, data in data_manager.user_data.items() if data["coins"] > 0]
    if top_list:
        top_player = max(top_list, key=lambda x: x[1])
        top_name = data_manager.get_user_name_by_id(top_player[0])
        top_league = data_manager.user_data[top_player[0]]["league"]
        top_str = f"{top_name} [{top_league}] — {format_number(int(top_player[1]))} монет"
    else:
        top_str = "—"

    msg = (
        f"📊 Статистика бота:
"
        f"👥 Активных игроков: {total_players}
"
        f"🪙 Всего монет в обороте: {format_number(int(total_coins))}
"
        f"💎 Всего Donat-коинов: {int(total_donate)}
"
        f"🏆 Топ-игрок: {top_str}"
    )
    return {"success": True, "message": msg}

def give_daily_reset(uid):
    """Сбрасывает ежедневный бонус"""
    try:
        uid = int(uid)
        data_manager.user_data[uid]["last_daily"] = 0
        data_manager.save_data()
        return {"success": True, "message": f"✅ Ежедневный бонус сброшен для {uid}."}
    except Exception as e:
        return {"success": False, "message": f"❌ Ошибка: {e}"}

def ban_user(uid):
    """Блокирует пользователя"""
    try:
        uid = int(uid)
        data_manager.user_data[uid]["auto_clicker"] = 0
        data_manager.user_data[uid]["last_daily"] = time.time() + 10 * 365 * 86400
        data_manager.save_data()
        return {"success": True, "message": f"⚠️ Пользователь {uid} заблокирован."}
    except Exception as e:
        return {"success": False, "message": f"❌ Ошибка: {e}"}

def test_achievements(uid):
    """Выдаёт все достижения"""
    try:
        uid = int(uid)
        data_manager.user_data[uid]["achievements"] = set(config.ACHIEVEMENTS.keys())
        data_manager.save_data()
        return {"success": True, "message": f"✅ Все достижения выданы пользователю {uid}."}
    except Exception as e:
        return {"success": False, "message": f"❌ Ошибка: {e}"}

def get_debug_info(user_id):
    """Получает отладочную информацию"""
    ud = data_manager.user_data[user_id]
    msg = (
        f"🔧 <b>Отладка</b>
"
        f"🪙 Монет: {format_number(int(ud['coins']))}
"
        f"💎 Donat: {ud['donate_coins']}
"
        f"🖱 Кликов: {format_number(ud['clicks'])}
"
        f"⚡ Сила клика: {ud['click_power']}
"
        f"🤖 Автокликер: {ud['auto_clicker']} монет/мин
"
        f"🏅 Лига: {ud['league']}
"
        f"👑 Звание: {ud['title']}
"
        f"💎 Premium: {'Да' if is_premium_active(ud) else 'Нет'}"
    )
    return msg
