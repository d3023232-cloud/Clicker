import time
import json
import signal
import os
import random
import asyncio
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, PreCheckoutQueryHandler

# === КОНФИГУРАЦИЯ ===
BOT_TOKEN = 'ВАШ_ТОКЕН'  # ← Получите в @BotFather
ADMIN_ID = 0  # ← Ваш Telegram ID (узнать: @userinfobot)
ADMIN_IDS = [ADMIN_ID]  # Добавьте сюда ID других админов, если нужно
DATA_FILE = 'clicker_data.json'
YOUR_BOT_USERNAME = "your_clicker_bot"  # ← Замените на имя вашего бота в Telegram

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def format_number(n: int) -> str:
    """Форматирует число с разделителями: 1234567 → 1,234,567"""
    return f"{int(n):,}"

def generate_crash_multiplier() -> float:
    r = random.random()
    if r >= 0.9999:
        return 100.0
    crash = 0.99 / (1 - r)
    return min(100.0, round(crash, 2))

def get_time_greeting():
    hour = time.localtime().tm_hour
    if 0 <= hour < 7:
        return "🌙 Сладких снов!"
    elif 7 <= hour < 12:
        return "☀️ Доброе утро!"
    elif 12 <= hour < 18:
        return "🌤 Добрый день!"
    else:
        return "🌆 Добрый вечер!"

# === НАПОМИНАНИЯ ===
REMINDER_MESSAGES = [
    "Пойдем играть! У тебя наверняка накапала приличная сумма в автокликире 😏/start",
    "Ты пропустил кучу монет! Загляни в бота 🪙/start",
    "Твой автокликер плачет без тебя 💧/start",
    "Срочно! Твой баланс растёт, а ты не смотришь! 👀/start",
    "Нажми 'Клик!' — и получи бонус! 🎁/start",
    "Ты в шаге от новой лиги! Проверь свой прогресс 🏆/start",
    "Твой автокликер заработал для тебя — забери! 🤖/start",
    "Не спи! Монеты ждут тебя! 💰/start",
    "Ты не поверишь, сколько у тебя монет... 👀/start",
    "Загляни в магазин — там новое улучшение! 🔧/start",
    "Твой профиль скучает без тебя! 👤/start",
    "Пора обновить звание! У тебя почти хватает 🪙/start",
    "Кто-то только что обогнал тебя в топе! Беги! 🏃‍♂️/start",
    "Ты пропустил ежедневный бонус! Забери его 🎁/start",
    "Твой автокликер работает на износ — забери прибыль! ⚙️/start",
    "Сыграй в краш — сегодня твой день удачи! 🍀/start",
    "Ты не играл уже час! Твой баланс замерз ❄️/start",
    "Нажми 'Клик!' — и получи +10% к силе клика на 5 минут! ⚡/start",
    "Ты в 1 клике от нового достижения! 🏅/start",
    "Твой баланс перевалил за миллион! Поздравляю! 🎉/start",
    "Загляни в мини-игры — там джекпот! 🎰/start",
    "Ты не использовал автокликер целый день! Активируй его! 🤖/start",
    "Твой профиль выглядит грустно без тебя 😢/start",
    "Проверь, сколько монет ты заработал за это время! 📈/start",
    "Ты пропустил шанс выиграть в рулетке! 🔴⚫/start",
    "Твой автокликер устал — дай ему отдохнуть (и забери монеты) 😴/start",
    "Срочно! Ограниченное улучшение в магазине! ⏳/start",
    "Ты почти достиг легендарной лиги! 💎/start",
    "Твой баланс растёт, а ты читаешь это сообщение? 😏/start",
    "Не забудь про ежедневный бонус — он ждёт тебя! 🎁/start"
]

# === ЛИГИ ===
LEAGUES = [
    (0, "🥉 №1Бронзовая"),
    (1000000, "🥈 №1Серебряная"),
    (10000000, "🥇 №3Золотая"),
    (100000000, "💎 №4Алмазная"),
    (500000000, "💚 №5Изумрудная"),
    (1000000000, "❤️ №6Рубиновая"),
    (50000000000, "⚡️ №7Божественная"),
    (100000000000, "🌌 №8Галактическая"),
    (500000000000, "🏆 №9Легендарная")
]

def get_league(coins):
    for min_coins, name in reversed(LEAGUES):
        if coins >= min_coins:
            return name
    return LEAGUES[0][1]

# === ГЛОБАЛЬНЫЕ ДАННЫЕ ===
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

ACHIEVEMENTS = {
    "first_click": {"name": "Первый клик!", "desc": "Сделать первый клик"},
    "click_100": {"name": "Клик-машина", "desc": "100 кликов"},
    "rich_100": {"name": "Первые 100 монет!", "desc": "Накопить 100 монет"},
    "buy_upgrade": {"name": "Инвестор", "desc": "Купить первое улучшение"},
    "auto_owner": {"name": "Робо-помощник", "desc": "Приобрести автокликер"}
}

UPGRADES = {
    "double_click": {
        "name": "Удвоитель клика",
        "cost": 10,
        "effect": 2.0,
        "type": "click_power"
    },
    "auto_clicker": {
        "name": "Автокликер",
        "cost": 30,
        "effect": 5.0,
        "type": "auto_clicker"
    }
}

TITLES = {
    "novice": {"name": "Новичок", "cost": 0, "desc": "Только начал путь кликера"},
    "clicker": {"name": "Кликер", "cost": 100, "desc": "Уже не новичок!"},
    "millionaire": {"name": "Миллионер", "cost": 1000, "desc": "Богатый кликер!"},
    "legend": {"name": "Легенда", "cost": 5000, "desc": "Живая легенда мира кликеров!"}
}

DONAT_SHOP = {
    "premium": {
        "name": "💎 Premium-статус",
        "cost": 50,
        "stars": 100,
        "desc": "×2 к автоклику, ×1.5 к клику, +50 монет ежедневно"
    },
    "bonus_100": {
        "name": "💰 +100 монет",
        "cost": 5,
        "stars": 10,
        "desc": "Мгновенно +100 монет"
    },
    "click_power_5": {
        "name": "⚡ +5 к силе клика",
        "cost": 20,
        "stars": 40,
        "desc": "Навсегда +5 к силе клика"
    }
}

# === ФУНКЦИИ СОХРАНЕНИЯ/ЗАГРУЗКИ ===
def save_data():
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

        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "user_data": serializable_user_data,
                "user_names": user_names
            }, f, ensure_ascii=False, indent=2)
        print("💾 Данные сохранены.")
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")

def load_data():
    global user_data, user_names
    if not os.path.exists(DATA_FILE):
        print("📁 Файл данных не найден. Создаётся новый.")
        return

    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
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

def get_user_name(user):
    return user.full_name if user.full_name else f"ID{user.id}"

def check_achievements(user_id):
    ud = user_data[user_id]
    unlocked = []

    if ud["clicks"] >= 1 and "first_click" not in ud["achievements"]:
        ud["achievements"].add("first_click")
        unlocked.append("first_click")
    if ud["clicks"] >= 100 and "click_100" not in ud["achievements"]:
        ud["achievements"].add("click_100")
        unlocked.append("click_100")
    if ud["coins"] >= 100 and "rich_100" not in ud["achievements"]:
        ud["achievements"].add("rich_100")
        unlocked.append("rich_100")

    if unlocked:
        save_data()
    return unlocked

def update_league(user_id):
    coins = user_data[user_id]["coins"]
    user_data[user_id]["league"] = get_league(coins)

def is_premium_active(user_id):
    ud = user_data[user_id]
    if not ud["premium"]:
        return False
    if ud["premium_until"] == 0:
        return True  # навсегда
    return time.time() < ud["premium_until"]

def get_profile_text(user_id: int) -> str:
    ud = user_data[user_id]
    premium_badge = "💎" if is_premium_active(user_id) else ""

    if ud["achievements"]:
        ach_list = [ACHIEVEMENTS.get(k, {}).get("name", k) for k in ud["achievements"]]
        achievements_str = ", ".join(ach_list)
    else:
        achievements_str = "—"

    top_list = sorted(
        [(uid, data["coins"]) for uid, data in user_data.items() if data["coins"] > 0],
        key=lambda x: x[1],
        reverse=True
    )
    try:
        rank = next(i for i, (uid, _) in enumerate(top_list, 1) if uid == user_id)
        rank_str = f"#{rank}"
    except StopIteration:
        rank_str = "—"

    current_cost = next((t["cost"] for t in TITLES.values() if t["name"] == ud["title"]), 0)
    next_titles = [t for t in TITLES.values() if t["cost"] > current_cost]
    if next_titles:
        next_title = min(next_titles, key=lambda x: x["cost"])
        needed = next_title["cost"] - ud["coins"]
        if needed <= 0:
            progress_str = f"✅ Уже доступно: {next_title['name']}!"
        else:
            progress_str = f"{format_number(needed)} монет до «{next_title['name']}»"
    else:
        progress_str = "👑 Вы достигли высшего звания!"

    msg = (
        f"👤 <b>Ваш профиль</b> {premium_badge}\n\n"
        f"🪙 Монет: <b>{format_number(int(ud['coins']))}</b>\n"
        f"💎 Donat-коины: <b>{ud['donate_coins']}</b>\n"
        f"🖱 Кликов: <b>{format_number(ud['clicks'])}</b>\n"
        f"⚡ Сила клика: <b>{ud['click_power']}</b>\n"
        f"🤖 Автокликер: <b>{ud['auto_clicker']}</b> монет/мин\n"
        f"🏅 Лига: <b>{ud['league']}</b>\n"
        f"👑 Звание: <b>{ud['title']}</b>\n"
        f"🏆 Место в топе: <b>{rank_str}</b>\n"
        f"shortcode_to_emoji Достижения: <b>{achievements_str}</b>"
    )
    return msg

def get_main_menu():
    """Главное меню с кнопками по парам + Клик внизу"""
    keyboard = [
        # Ряд 1
        [InlineKeyboardButton("🏆 Топ", callback_data='top'),
         InlineKeyboardButton("🛒 Магазин", callback_data='shop')],

        # Ряд 2
        [InlineKeyboardButton("🎮 Мини-игры", callback_data='minigames'),
         InlineKeyboardButton("🎁 Ежедневный бонус", callback_data='daily')],

        # Ряд 3
        [InlineKeyboardButton("💎 Donat-магазин", callback_data='donat_shop'),
         InlineKeyboardButton("🤝 Рефералка", callback_data='referral')],

        # Ряд 4
        [InlineKeyboardButton("🏅 Достижения", callback_data='achievements'),
         InlineKeyboardButton("👤 Мой профиль", callback_data='my_profile')],

        # Ряд 5: КЛИК в самом низу (одна кнопка)
        [InlineKeyboardButton("🖱 Клик!", callback_data='click')]
    ]
    return InlineKeyboardMarkup(keyboard)

# === ФОНОВАЯ ЗАДАЧА: НАПОМИНАНИЯ ===
async def send_reminders(context: ContextTypes.DEFAULT_TYPE):
    now = time.time()
    for user_id, ud in list(user_data.items()):
        if not ud.get("reminders_enabled", True):
            continue
        last = ud.get("last_reminder", 0)
        if now - last >= random.randint(3600, 10800):  # 1–3 часа
            try:
                msg = random.choice(REMINDER_MESSAGES)
                await context.bot.send_message(chat_id=user_id, text=f"🔔 {msg}")
                user_data[user_id]["last_reminder"] = now
                save_data()
            except Exception:
                pass

# === ОБРАБОТЧИКИ ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    user_names[user_id] = get_user_name(user)

    # Реферальная система
    if context.args and context.args[0].startswith('ref'):
        try:
            referrer_id = int(context.args[0][3:])
            if referrer_id != user_id and user_data[user_id]["referrer_id"] is None:
                user_data[user_id]["referrer_id"] = referrer_id
                user_data[referrer_id]["donate_coins"] += 2
                save_data()
                try:
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text="🎁 Вы получили 2 Donat-коина за приглашённого друга!"
                    )
                except:
                    pass
        except:
            pass

    save_data()
    greeting = get_time_greeting()
    ref_link = f"https://t.me/{YOUR_BOT_USERNAME}?start=ref{user_id}"
    await update.message.reply_text(
        f"{greeting}\n"
        f"🎮 Добро пожаловать в Clicker Bot!\n\n"
        f"🔗 Ваша реферальная ссылка:\n<code>{ref_link}</code>",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = user.id
    user_names[user_id] = get_user_name(user)

    # === АДМИН-ПАНЕЛЬ: кнопки ===
    if query.data.startswith('admin_cmd_'):
        cmd = query.data[10:]  # Убираем 'admin_cmd_'
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
        desc = descriptions.get(cmd, "Команда не найдена.")
        await query.answer(desc, show_alert=True)
        return  # Возвращаемся, чтобы не вызвать другие обработчики

    if query.data == 'click':
        ud = user_data[user_id]
        now = time.time()
        auto_income = 0
        last_click = ud.get("last_click", now)
        seconds_passed = now - last_click

        # Учитываем Premium
        auto_clicker_rate = ud["auto_clicker"]
        if is_premium_active(user_id):
            auto_clicker_rate *= 2

        if seconds_passed >= 1 and auto_clicker_rate > 0:
            minutes_passed = seconds_passed / 60
            auto_income = auto_clicker_rate * minutes_passed
            ud["coins"] += auto_income

        coins_earned = ud["click_power"]
        if is_premium_active(user_id):
            coins_earned *= 1.5

        ud["clicks"] += 1
        ud["coins"] += coins_earned
        ud["last_click"] = now
        update_league(user_id)
        save_data()

        new_achs = check_achievements(user_id)
        ach_msg = ""
        if new_achs:
            ach_names = [ACHIEVEMENTS[aid]["name"] for aid in new_achs]
            ach_msg = "\n\n🎉 Новое достижение: " + ", ".join(ach_names) + "!"

        text = (
            f"🖱 Вы кликнули!\n"
            f"💰 +{format_number(int(coins_earned))} монет от клика\n"
            f"🤖 +{format_number(int(auto_income))} монет от автокликера\n"
            f"🪙 Всего монет: {format_number(int(ud['coins']))}\n"
            f"⚡ Сила клика: {ud['click_power']}"
            + ach_msg
        )
        await query.edit_message_text(text=text, reply_markup=get_main_menu())

    elif query.data == 'top':
        top_list = sorted(
            [(uid, data["coins"]) for uid, data in user_data.items() if data["coins"] > 0],
            key=lambda x: x[1],
            reverse=True
        )[:5]
        msg = "🏆 Топ-5 богачей:\n"
        for i, (uid, coins) in enumerate(top_list, 1):
            name = user_names.get(uid, f"ID{uid}")
            league = user_data[uid]["league"]
            premium_badge = "💎" if is_premium_active(uid) else ""
            msg += f"{i}. {name} {premium_badge} [{league}] — {format_number(int(coins))} монет\n"
        await query.edit_message_text(text=msg, reply_markup=get_main_menu())

    elif query.data == 'shop':
        keyboard = [
            [InlineKeyboardButton("🔧 Улучшения", callback_data='shop_upgrades')],
            [InlineKeyboardButton("🏅 Звания", callback_data='shop_titles')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🛒 Магазин:", reply_markup=reply_markup)

    elif query.data == 'shop_upgrades':
        ud = user_data[user_id]
        coins = ud["coins"]
        keyboard = []
        for key, upg in UPGRADES.items():
            if coins >= upg["cost"]:
                btn = InlineKeyboardButton(f"Купить: {upg['name']} ({format_number(upg['cost'])} 🪙)", callback_data=f'buy_upg_{key}')
            else:
                btn = InlineKeyboardButton(f"🔒 {upg['name']} ({format_number(upg['cost'])} 🪙)", callback_data='noop')
            keyboard.append([btn])
        keyboard.append([InlineKeyboardButton("⬅️ Назад в магазин", callback_data='shop')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🔧 Улучшения:", reply_markup=reply_markup)

    elif query.data == 'shop_titles':
        ud = user_data[user_id]
        coins = ud["coins"]
        current_title = ud["title"]
        keyboard = []
        for key, title in TITLES.items():
            if title["name"] == current_title:
                btn = InlineKeyboardButton(f"✅ {title['name']} — {title['desc']}", callback_data='noop')
            elif coins >= title["cost"]:
                btn = InlineKeyboardButton(f"Купить: {title['name']} ({format_number(title['cost'])} 🪙)", callback_data=f'buy_title_{key}')
            else:
                btn = InlineKeyboardButton(f"🔒 {title['name']} ({format_number(title['cost'])} 🪙)", callback_data='noop')
            keyboard.append([btn])
        keyboard.append([InlineKeyboardButton("⬅️ Назад в магазин", callback_data='shop')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🏅 Звания (покупаются за монеты):", reply_markup=reply_markup)

    elif query.data == 'daily':
        now = time.time()
        ud = user_data[user_id]
        if now - ud["last_daily"] < 86400:
            hours = int((86400 - (now - ud["last_daily"])) / 3600) + 1
            await query.edit_message_text(
                f"🎁 Бонус можно получить через {hours} ч.",
                reply_markup=get_main_menu()
            )
        else:
            bonus = 50 if is_premium_active(user_id) else 20
            ud["coins"] += bonus
            ud["last_daily"] = now
            update_league(user_id)
            save_data()
            await query.edit_message_text(
                f"🎁 Получено {format_number(bonus)} монет!\nВозвращайтесь завтра!",
                reply_markup=get_main_menu()
            )

    elif query.data == 'achievements':
        ud = user_data[user_id]
        msg = "🏅 Ваши достижения:\n"
        for key, ach in ACHIEVEMENTS.items():
            status = "✅" if key in ud["achievements"] else "❌"
            msg += f"{status} {ach['name']} — {ach['desc']}\n"
        msg += f"\n👑 Ваше звание: {ud['title']}"
        await query.edit_message_text(msg, reply_markup=get_main_menu())

    elif query.data == 'my_profile':
        msg = get_profile_text(user_id)
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=get_main_menu())

    elif query.data == 'referral':
        ref_link = f"https://t.me/{YOUR_BOT_USERNAME}?start=ref{user_id}"
        ud = user_data[user_id]
        ref_count = len([u for u in user_data.values() if u.get("referrer_id") == user_id])
        msg = (
            f"🤝 <b>Реферальная система</b>\n\n"
            f"🔗 Ваша ссылка:\n<code>{ref_link}</code>\n\n"
            f"👥 Приглашено: <b>{ref_count}</b> друзей\n"
            f"💎 За каждого: <b>2 Donat-коина</b>\n"
            f"💰 Всего получено: <b>{ud['donate_coins']}</b> Donat-коинов"
        )
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=get_main_menu())

    elif query.data == 'donat_shop':
        ud = user_data[user_id]
        keyboard = []
        for key, item in DONAT_SHOP.items():
            btn = InlineKeyboardButton(
                f"{item['name']} ({item['stars']} ⭐)",
                callback_data=f'buy_stars_{key}'
            )
            keyboard.append([btn])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='back')])
        await query.edit_message_text(
            "💎 <b>Donat-магазин (оплата звёздами)</b>\nПокупайте за ⭐:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith('buy_stars_'):
        print(f"DEBUG: Получена кнопка buy_stars_ от {user_id}")  # ← Для проверки
        item_key = query.data[10:]
        if item_key not in DONAT_SHOP:
            print(f"DEBUG: item_key {item_key} не найден в DONAT_SHOP")  # ← Для проверки
            return
        item = DONAT_SHOP[item_key]

        try:
            await context.bot.send_invoice(
                chat_id=user_id,
                title=item['name'],
                description=item['desc'],
                payload=f"donat_{item_key}",
                provider_token="",  # Пустой для звёзд
                currency="XTR",     # Telegram Stars
                prices=[LabeledPrice(label="Цена", amount=item['stars'])],
                max_tip_amount=0,
                suggested_tip_amounts=[],
                start_parameter="buy"
            )
        except Exception as e:
            print(f"❌ Ошибка при отправке инвойса: {e}")  # ← Важно!
            await query.edit_message_text("❌ Ошибка при создании инвойса.")

    # === МИНИ-ИГРЫ ===
    elif query.data == 'minigames':
        keyboard = [
            [InlineKeyboardButton("💥 Краш (20–1 000 000 🪙)", callback_data='game_crash_start')],
            [InlineKeyboardButton("🎰 Рулетка (20–1 000 000 🪙)", callback_data='game_roulette_start')],
            [InlineKeyboardButton("⚔️ Дуэль (100–1 000 000 🪙)", callback_data='game_duel_start')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='back')]
        ]
        await query.edit_message_text("🎮 Выберите мини-игру:", reply_markup=InlineKeyboardMarkup(keyboard))

    # === КРАШ ===
    elif query.data == 'game_crash_start':
        ud = user_data[user_id]
        if ud["coins"] < 20:
            await query.answer("❌ Нужно минимум 20 монет!", show_alert=True)
            return
        msg = (
            "💥 <b>Краш-игра</b>\n"
            "Ставка от 20 до 1 000 000 монет.\n\n"
            "<i>Введите ставку в чат (например: 100)</i>"
        )
        await query.edit_message_text(msg, parse_mode="HTML")
        context.user_data["crash_state"] = "bet"
        context.user_data["crash_user_id"] = user_id

    elif query.data.startswith('crash_multiplier_'):
        try:
            multiplier = float(query.data.split('_')[2])
            bet = context.user_data.get("crash_bet")
            crash_user_id = context.user_data.get("crash_user_id")
            if bet is None or crash_user_id != user_id:
                await query.edit_message_text("❌ Сессия устарела. Начните заново.", reply_markup=get_main_menu())
                return

            ud = user_data[user_id]
            if ud["coins"] < bet:
                await query.edit_message_text("❌ Недостаточно монет!", reply_markup=get_main_menu())
                return

            bot_multiplier = generate_crash_multiplier()
            await query.edit_message_text("🚀 Ракета запускается...")
            await asyncio.sleep(1)
            await query.edit_message_text(f"📈 Множитель растёт... {bot_multiplier}x")

            if bot_multiplier >= multiplier:
                win = int(bet * multiplier)
                ud["coins"] += win
                update_league(user_id)
                save_data()
                await query.edit_message_text(
                    f"✅ <b>УСПЕХ!</b>\n"
                    f"Ваш множитель: {multiplier}x\n"
                    f"Взрыв: {bot_multiplier}x\n"
                    f"Вы выиграли: <b>+{format_number(win)}</b> монет! 🎉",
                    parse_mode="HTML",
                    reply_markup=get_main_menu()
                )
            else:
                ud["coins"] -= bet
                update_league(user_id)
                save_data()
                await query.edit_message_text(
                    f"💥 <b>ВЗРЫВ!</b>\n"
                    f"Ваш множитель: {multiplier}x\n"
                    f"Взрыв: {bot_multiplier}x\n"
                    f"Вы потеряли: <b>{format_number(bet)}</b> монет 😢",
                    parse_mode="HTML",
                    reply_markup=get_main_menu()
                )
            context.user_data.pop("crash_state", None)
            context.user_data.pop("crash_bet", None)
            context.user_data.pop("crash_user_id", None)
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {e}", reply_markup=get_main_menu())

    # === РУЛЕТКА ===
    elif query.data == 'game_roulette_start':
        ud = user_data[user_id]
        if ud["coins"] < 20:
            await query.answer("❌ Нужно минимум 20 монет!", show_alert=True)
            return
        msg = (
            "🎰 <b>Рулетка</b>\n"
            "Ставка от 20 до 1 000 000 монет.\n"
            "Выберите цвет:\n"
            "• 🔴 Красное (×1.9)\n"
            "• ⚫ Чёрное (×1.9)\n"
            "• 🟢 Зелёное (×9.0, шанс 10%)\n\n"
            "<i>Введите ставку в чат</i>"
        )
        await query.edit_message_text(msg, parse_mode="HTML")
        context.user_data["roulette_state"] = "bet"
        context.user_data["roulette_user_id"] = user_id

    elif query.data.startswith('roulette_color_'):
        color = query.data.split('_')[2]
        bet = context.user_data.get("roulette_bet")
        roulette_user_id = context.user_data.get("roulette_user_id")
        if bet is None or roulette_user_id != user_id:
            await query.edit_message_text("❌ Сессия устарела. Начните заново.", reply_markup=get_main_menu())
            return

        ud = user_data[user_id]
        if ud["coins"] < bet:
            await query.edit_message_text("❌ Недостаточно монет!", reply_markup=get_main_menu())
            return

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
            message = f"✅ Выпало {color}! Вы выиграли <b>+{format_number(win)}</b> монет!"
        else:
            ud["coins"] -= bet
            message = f"❌ Выпало {result}. Вы потеряли <b>{format_number(bet)}</b> монет."

        update_league(user_id)
        save_data()
        await query.edit_message_text(
            f"🎰 <b>Рулетка</b>\n{message}\n\n🪙 Баланс: {format_number(int(ud['coins']))}",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
        context.user_data.pop("roulette_state", None)
        context.user_data.pop("roulette_bet", None)
        context.user_data.pop("roulette_user_id", None)

    # === ДУЭЛЬ ===
    elif query.data == 'game_duel_start':
        ud = user_data[user_id]
        if ud["coins"] < 100:
            await query.answer("❌ Нужно минимум 100 монет!", show_alert=True)
            return
        msg = (
            "⚔️ <b>Дуэль с ботом</b>\n"
            "Ставка от 100 до 1 000 000 монет.\n"
            "Шанс победы: 48% (бот берёт 4% комиссии).\n\n"
            "<i>Введите ставку в чат</i>"
        )
        await query.edit_message_text(msg, parse_mode="HTML")
        context.user_data["duel_state"] = "bet"
        context.user_data["duel_user_id"] = user_id

    # === ПОКУПКИ ===
    elif query.data.startswith('buy_upg_'):
        upg_key = query.data[8:]
        if upg_key not in UPGRADES:
            return
        ud = user_data[user_id]
        upg = UPGRADES[upg_key]
        if ud["coins"] >= upg["cost"]:
            ud["coins"] -= upg["cost"]
            if upg["type"] == "click_power":
                old_power = ud["click_power"]
                ud["click_power"] += upg["effect"]
                await query.edit_message_text(
                    f"✅ Куплено: {upg['name']}!\n"
                    f"⚡ Сила клика: {old_power} → {ud['click_power']}",
                    reply_markup=get_main_menu()
                )
            elif upg["type"] == "auto_clicker":
                old_auto = ud["auto_clicker"]
                ud["auto_clicker"] += upg["effect"]
                if "auto_owner" not in ud["achievements"]:
                    ud["achievements"].add("auto_owner")
                    await query.answer("🎉 Открыто достижение: Робо-помощник!", show_alert=True)
                await query.edit_message_text(
                    f"✅ Куплен: {upg['name']}!\n"
                    f"🤖 Автокликер: {old_auto} → {ud['auto_clicker']} монет/мин",
                    reply_markup=get_main_menu()
                )
            if "buy_upgrade" not in ud["achievements"]:
                ud["achievements"].add("buy_upgrade")
            update_league(user_id)
            save_data()
        else:
            await query.answer("❌ Недостаточно монет!", show_alert=True)

    elif query.data.startswith('buy_title_'):
        title_key = query.data[11:]
        if title_key not in TITLES:
            return
        ud = user_data[user_id]
        title = TITLES[title_key]
        if ud["coins"] >= title["cost"]:
            ud["coins"] -= title["cost"]
            ud["title"] = title["name"]
            update_league(user_id)
            save_data()
            await query.edit_message_text(f"👑 Звание '{title['name']}' установлено!", reply_markup=get_main_menu())
        else:
            await query.answer("❌ Недостаточно монет!", show_alert=True)

    elif query.data == 'back' or query.data == 'noop':
        await query.edit_message_text("🎮 Главное меню:", reply_markup=get_main_menu())

# === КОМАНДЫ ===
async def mm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_names[user_id] = get_user_name(update.effective_user)
    msg = get_profile_text(user_id)
    await update.message.reply_text(msg, parse_mode="HTML")

# === АДМИН ПАНЕЛЬ ===
async def admins_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Проверяем, является ли пользователь админом
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return

    # Текст сообщения
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

    msg = "🔐 <b>Админ-панель</b>\n\n" + "\n".join(commands_list)

    # Создаём кнопки
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

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)

# === ЕДИНЫЙ ОБРАБОТЧИК СТАВОК ===
async def handle_any_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Рулетка
    if context.user_data.get("roulette_state") == "bet" and context.user_data.get("roulette_user_id") == user_id:
        await handle_roulette_bet_internal(update, context)
        return

    # Краш
    if context.user_data.get("crash_state") == "bet" and context.user_data.get("crash_user_id") == user_id:
        await handle_crash_bet_internal(update, context)
        return

    # Дуэль
    if context.user_data.get("duel_state") == "bet" and context.user_data.get("duel_user_id") == user_id:
        await handle_duel_bet_internal(update, context)
        return

async def handle_roulette_bet_internal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        bet = int(update.message.text)
        if bet < 20:
            await update.message.reply_text("❌ Минимальная ставка: 20 монет.")
            return
        if bet > 1_000_000:
            await update.message.reply_text("❌ Максимальная ставка: 1 000 000 монет.")
            return
        if user_data[user_id]["coins"] < bet:
            await update.message.reply_text("❌ Недостаточно монет!")
            return

        context.user_data["roulette_bet"] = bet
        keyboard = [
            [InlineKeyboardButton("🔴 Красное", callback_data='roulette_color_red')],
            [InlineKeyboardButton("⚫ Чёрное", callback_data='roulette_color_black')],
            [InlineKeyboardButton("🟢 Зелёное", callback_data='roulette_color_green')],
            [InlineKeyboardButton("⬅️ Отмена", callback_data='minigames')]
        ]
        await update.message.reply_text(
            f"🎰 Ставка: {format_number(bet)} монет\nВыберите цвет:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except ValueError:
        await update.message.reply_text("❌ Введите целое число (например: 100)")

async def handle_crash_bet_internal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        bet = int(update.message.text)
        if bet < 20:
            await update.message.reply_text("❌ Минимальная ставка: 20 монет.")
            return
        if bet > 1_000_000:
            await update.message.reply_text("❌ Максимальная ставка: 1 000 000 монет.")
            return
        if user_data[user_id]["coins"] < bet:
            await update.message.reply_text("❌ Недостаточно монет!")
            return

        context.user_data["crash_bet"] = bet
        context.user_data["crash_state"] = "multiplier"
        multipliers = [1.25, 1.5, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0, 100.0]
        keyboard = []
        row = []
        for m in multipliers:
            row.append(InlineKeyboardButton(f"{m}x", callback_data=f'crash_multiplier_{m}'))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("⬅️ Отмена", callback_data='minigames')])
        await update.message.reply_text(
            f"💥 Ставка: {format_number(bet)} монет\nВыберите множитель:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except ValueError:
        await update.message.reply_text("❌ Введите целое число (например: 100)")

async def handle_duel_bet_internal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        bet = int(update.message.text)
        if bet < 100:
            await update.message.reply_text("❌ Минимальная ставка: 100 монет.")
            return
        if bet > 1_000_000:
            await update.message.reply_text("❌ Максимальная ставка: 1 000 000 монет.")
            return
        if user_data[user_id]["coins"] < bet:
            await update.message.reply_text("❌ Недостаточно монет!")
            return

        if random.random() < 0.48:
            win = int(bet * 0.96)
            user_data[user_id]["coins"] += win
            message = f"✅ Вы победили! Получено <b>+{format_number(win)}</b> монет (с учётом комиссии)."
        else:
            user_data[user_id]["coins"] -= bet
            message = f"❌ Вы проиграли <b>{format_number(bet)}</b> монет."

        update_league(user_id)
        save_data()
        await update.message.reply_text(
            f"⚔️ <b>Дуэль</b>\n{message}\n\n🪙 Баланс: {format_number(int(user_data[user_id]['coins']))}",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
        context.user_data.pop("duel_state", None)
        context.user_data.pop("duel_user_id", None)
    except ValueError:
        await update.message.reply_text("❌ Введите целое число (например: 500)")

# === АДМИНКА ===
async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    user_id = update.effective_user.id
    ud = user_data[user_id]
    msg = (
        f"🔧 <b>Отладка</b>\n"
        f"🪙 Монет: {format_number(int(ud['coins']))}\n"
        f"💎 Donat: {ud['donate_coins']}\n"
        f"🖱 Кликов: {format_number(ud['clicks'])}\n"
        f"⚡ Сила клика: {ud['click_power']}\n"
        f"🤖 Автокликер: {ud['auto_clicker']} монет/мин\n"
        f"🏅 Лига: {ud['league']}\n"
        f"👑 Звание: {ud['title']}\n"
        f"💎 Premium: {'Да' if is_premium_active(user_id) else 'Нет'}"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def add_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Используйте: /add_coins <user_id> <amount>")
        return
    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
        user_data[target_id]["coins"] += amount
        update_league(target_id)
        save_data()
        await update.message.reply_text(f"✅ Добавлено {format_number(amount)} монет пользователю {target_id}.")
    except ValueError:
        await update.message.reply_text("❌ Ошибка: ID и сумма должны быть числами.")

async def get_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Используйте: /get_user <user_id>")
        return
    try:
        uid = int(context.args[0])
        ud = user_data[uid]
        name = user_names.get(uid, f"ID{uid}")
        msg = (
            f"👤 Пользователь: {name} (ID: {uid})\n"
            f"🪙 Монет: {format_number(int(ud['coins']))}\n"
            f"💎 Donat-коины: {ud['donate_coins']}\n"
            f"🖱 Кликов: {format_number(ud['clicks'])}\n"
            f"⚡ Сила клика: {ud['click_power']}\n"
            f"🤖 Автокликер: {ud['auto_clicker']} монет/мин\n"
            f"🏅 Лига: {ud['league']}\n"
            f"👑 Звание: {ud['title']}\n"
            f"💎 Premium: {'Да' if is_premium_active(uid) else 'Нет'}\n"
            f"shortcode_to_emoji Достижения: {', '.join(ACHIEVEMENTS.get(k, {}).get('name', k) for k in ud['achievements']) or '—'}"
        )
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def reset_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Используйте: /reset_user <user_id>")
        return
    try:
        uid = int(context.args[0])
        user_data[uid] = {
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
        await update.message.reply_text(f"✅ Данные пользователя {uid} сброшены.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    total_players = len([u for u in user_data if user_data[u]["coins"] > 0 or user_data[u]["clicks"] > 0])
    total_coins = sum(u["coins"] for u in user_data.values())
    total_donate = sum(u["donate_coins"] for u in user_data.values())
    top_list = [(uid, data["coins"]) for uid, data in user_data.items() if data["coins"] > 0]
    if top_list:
        top_player = max(top_list, key=lambda x: x[1])
        top_name = user_names.get(top_player[0], f"ID{top_player[0]}")
        top_league = user_data[top_player[0]]["league"]
        top_str = f"{top_name} [{top_league}] — {format_number(int(top_player[1]))} монет"
    else:
        top_str = "—"
    msg = (
        f"📊 Статистика бота:\n"
        f"👥 Активных игроков: {total_players}\n"
        f"🪙 Всего монет в обороте: {format_number(int(total_coins))}\n"
        f"💎 Всего Donat-коинов: {int(total_donate)}\n"
        f"🏆 Топ-игрок: {top_str}"
    )
    await update.message.reply_text(msg)

async def give_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Используйте: /give_daily <user_id>")
        return
    try:
        uid = int(context.args[0])
        user_data[uid]["last_daily"] = 0
        save_data()
        await update.message.reply_text(f"✅ Ежедневный бонус сброшен для {uid}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Используйте: /ban_user <user_id>")
        return
    try:
        uid = int(context.args[0])
        user_data[uid]["auto_clicker"] = 0
        user_data[uid]["last_daily"] = time.time() + 10 * 365 * 86400
        save_data()
        await update.message.reply_text(f"⚠️ Пользователь {uid} заблокирован.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def test_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Используйте: /test_achievements <user_id>")
        return
    try:
        uid = int(context.args[0])
        user_data[uid]["achievements"] = set(ACHIEVEMENTS.keys())
        save_data()
        await update.message.reply_text(f"✅ Все достижения выданы пользователю {uid}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if not context.args:
        await update.message.reply_text("Используйте: /broadcast <сообщение>")
        return
    message = ' '.join(context.args)
    sent_count = 0
    failed_count = 0

    active_users = [
        uid for uid, data in user_data.items()
        if data["coins"] > 0 or data["clicks"] > 0
    ]

    for uid in active_users:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 Рассылка от админа:\n\n{message}")
            sent_count += 1
        except Exception:
            failed_count += 1

    await update.message.reply_text(
        f"✅ Рассылка отправлена!\n"
        f"📬 Успешно: {sent_count}\n"
        f"❌ Не доставлено: {failed_count}"
    )

# === НОВЫЕ АДМИН-КОМАНДЫ ===
async def give_donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выдаёт Donat-коины: /give_donate <user_id> <amount>"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Используйте: /give_donate <user_id> <amount>")
        return
    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
        user_data[target_id]["donate_coins"] += amount
        save_data()
        await update.message.reply_text(f"✅ Выдано {amount} Donat-коинов пользователю {target_id}.")
    except ValueError:
        await update.message.reply_text("❌ Ошибка: ID и сумма должны быть числами.")

async def give_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выдаёт Premium на N дней: /give_premium <user_id> <days>"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Используйте: /give_premium <user_id> <days>")
        return
    try:
        target_id = int(context.args[0])
        days = int(context.args[1])
        if days == 0:
            user_data[target_id]["premium"] = True
            user_data[target_id]["premium_until"] = 0  # навсегда
        else:
            user_data[target_id]["premium"] = True
            user_data[target_id]["premium_until"] = time.time() + days * 86400
        save_data()
        await update.message.reply_text(f"✅ Premium выдан пользователю {target_id} на {days} дней.")
    except ValueError:
        await update.message.reply_text("❌ Ошибка: ID и дни должны быть числами.")

# === PAYMENT HANDLERS (Telegram Stars) ===
async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    # Всегда отвечаем OK, т.к. звёзды не требуют внешнего провайдера
    await query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    successful_payment = update.message.successful_payment
    payload = successful_payment.invoice_payload

    if payload.startswith("donat_"):
        item_key = payload[6:]
        if item_key in DONAT_SHOP:
            item = DONAT_SHOP[item_key]
            # Начисляем Donat-коины
            user_data[user_id]["donate_coins"] += item["cost"]
            save_data()
            await update.message.reply_text(
                f"✅ Оплата прошла успешно!\n"
                f"Вы получили: <b>{item['name']}</b> ({item['cost']} 💎)",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text("❌ Неизвестный товар.")
    else:
        await update.message.reply_text("❌ Неизвестный платеж.")

def signal_handler(sig, frame):
    print("\n🛑 Получен сигнал завершения. Сохраняем данные...")
    save_data()
    exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    load_data()

    application = Application.builder().token(BOT_TOKEN).build()

    # ✅ JobQueue (для v20+ — создаётся автоматически)
    job_queue = application.job_queue  # ← Просто получаем

    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mm", mm))
    application.add_handler(CommandHandler("admins", admins_panel))  # ← НОВОЕ: админ-панель
    application.add_handler(CommandHandler("debug", debug))
    application.add_handler(CommandHandler("add_coins", add_coins))
    application.add_handler(CommandHandler("get_user", get_user))
    application.add_handler(CommandHandler("reset_user", reset_user))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("give_daily", give_daily))
    application.add_handler(CommandHandler("ban_user", ban_user))
    application.add_handler(CommandHandler("test_achievements", test_achievements))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("give_donate", give_donate))
    application.add_handler(CommandHandler("give_premium", give_premium))

    # Callbacks и сообщения
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_any_bet))

    # 🌟 НОВОЕ: обработчики платежей через звёзды
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    # Фоновая задача
    job_queue.run_repeating(send_reminders, interval=1800, first=60)

    print("✅ Бот запущен!")
    application.run_polling()

if __name__ == '__main__':
    main()
