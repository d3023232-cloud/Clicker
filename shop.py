"""Точка входа бота"""
import signal
import os
import sys

# Добавляем текущую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, PreCheckoutQueryHandler
)

import config
import data_manager
from handlers import (
    start_handler, button_handler, mm_handler,
    admins_panel_handler, get_main_menu
)
from payments import pre_checkout_handler, successful_payment_handler
from reminders import send_reminders
from admin import (
    is_admin, add_coins, give_donate, give_premium,
    get_user_info, reset_user, get_stats, give_daily_reset,
    ban_user, test_achievements, get_debug_info
)
from utils import get_user_name, format_number

async def debug_command(update, context):
    """Команда /debug"""
    if not is_admin(update.effective_user.id):
        return
    user_id = update.effective_user.id
    msg = get_debug_info(user_id)
    await update.message.reply_text(msg, parse_mode="HTML")

async def add_coins_command(update, context):
    """Команда /add_coins"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Используйте: /add_coins <user_id> <amount>")
        return

    result = add_coins(context.args[0], context.args[1])
    await update.message.reply_text(result["message"])

async def give_donate_command(update, context):
    """Команда /give_donate"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Используйте: /give_donate <user_id> <amount>")
        return

    result = give_donate(context.args[0], context.args[1])
    await update.message.reply_text(result["message"])

async def give_premium_command(update, context):
    """Команда /give_premium"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Используйте: /give_premium <user_id> <days>")
        return

    result = give_premium(context.args[0], context.args[1])
    await update.message.reply_text(result["message"])

async def get_user_command(update, context):
    """Команда /get_user"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Используйте: /get_user <user_id>")
        return

    result = get_user_info(context.args[0])
    await update.message.reply_text(result["message"])

async def reset_user_command(update, context):
    """Команда /reset_user"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Используйте: /reset_user <user_id>")
        return

    result = reset_user(context.args[0])
    await update.message.reply_text(result["message"])

async def stats_command(update, context):
    """Команда /stats"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return

    result = get_stats()
    await update.message.reply_text(result["message"])

async def give_daily_command(update, context):
    """Команда /give_daily"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Используйте: /give_daily <user_id>")
        return

    result = give_daily_reset(context.args[0])
    await update.message.reply_text(result["message"])

async def ban_user_command(update, context):
    """Команда /ban_user"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Используйте: /ban_user <user_id>")
        return

    result = ban_user(context.args[0])
    await update.message.reply_text(result["message"])

async def test_achievements_command(update, context):
    """Команда /test_achievements"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Используйте: /test_achievements <user_id>")
        return

    result = test_achievements(context.args[0])
    await update.message.reply_text(result["message"])

async def broadcast_command(update, context):
    """Команда /broadcast"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if not context.args:
        await update.message.reply_text("Используйте: /broadcast <сообщение>")
        return

    message = ' '.join(context.args)
    sent_count = 0
    failed_count = 0

    active_users = [
        uid for uid, data in data_manager.user_data.items()
        if data["coins"] > 0 or data["clicks"] > 0
    ]

    for uid in active_users:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 Рассылка от админа:

{message}")
            sent_count += 1
        except Exception:
            failed_count += 1

    await update.message.reply_text(
        f"✅ Рассылка отправлена!
"
        f"📬 Успешно: {sent_count}
"
        f"❌ Не доставлено: {failed_count}"
    )

# === ОБРАБОТЧИК СТАВОК ===
async def handle_any_bet(update, context):
    """Единый обработчик ставок для мини-игр"""
    user_id = update.effective_user.id

    # Рулетка
    if context.user_data.get("roulette_state") == "bet" and context.user_data.get("roulette_user_id") == user_id:
        await handle_roulette_bet(update, context)
        return

    # Краш
    if context.user_data.get("crash_state") == "bet" and context.user_data.get("crash_user_id") == user_id:
        await handle_crash_bet(update, context)
        return

    # Дуэль
    if context.user_data.get("duel_state") == "bet" and context.user_data.get("duel_user_id") == user_id:
        await handle_duel_bet(update, context)
        return

async def handle_roulette_bet(update, context):
    """Обработка ставки в рулетке"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from minigames import validate_bet

    user_id = update.effective_user.id
    result = validate_bet(user_id, update.message.text, config.MIN_BET, config.MAX_BET)

    if not result["success"]:
        await update.message.reply_text(result["message"])
        return

    bet = result["bet"]
    context.user_data["roulette_bet"] = bet

    keyboard = [
        [InlineKeyboardButton("🔴 Красное", callback_data='roulette_color_red')],
        [InlineKeyboardButton("⚫ Чёрное", callback_data='roulette_color_black')],
        [InlineKeyboardButton("🟢 Зелёное", callback_data='roulette_color_green')],
        [InlineKeyboardButton("⬅️ Отмена", callback_data='minigames')]
    ]

    await update.message.reply_text(
        f"🎰 Ставка: {format_number(bet)} монет
Выберите цвет:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_crash_bet(update, context):
    """Обработка ставки в краше"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from minigames import validate_bet

    user_id = update.effective_user.id
    result = validate_bet(user_id, update.message.text, config.MIN_BET, config.MAX_BET)

    if not result["success"]:
        await update.message.reply_text(result["message"])
        return

    bet = result["bet"]
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
        f"💥 Ставка: {format_number(bet)} монет
Выберите множитель:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_duel_bet(update, context):
    """Обработка ставки в дуэли"""
    from minigames import validate_bet, process_duel_game

    user_id = update.effective_user.id
    result = validate_bet(user_id, update.message.text, config.MIN_DUEL_BET, config.MAX_BET)

    if not result["success"]:
        await update.message.reply_text(result["message"])
        return

    bet = result["bet"]
    result = process_duel_game(user_id, bet)

    await update.message.reply_text(
        f"⚔️ <b>Дуэль</b>
{result['message']}

🪙 Баланс: {format_number(int(result['balance']))}",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

    context.user_data.pop("duel_state", None)
    context.user_data.pop("duel_user_id", None)

def signal_handler(sig, frame):
    """Обработчик сигналов завершения"""
    print("\n🛑 Получен сигнал завершения. Сохраняем данные...")
    data_manager.save_data()
    exit(0)

def main():
    """Главная функция запуска бота"""
    # Настройка обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Загрузка данных
    data_manager.load_data()

    # Создание приложения
    application = Application.builder().token(config.BOT_TOKEN).build()

    # Получение JobQueue
    job_queue = application.job_queue

    # === РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ===

    # Команды
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("mm", mm_handler))
    application.add_handler(CommandHandler("admins", admins_panel_handler))

    # Админ команды
    application.add_handler(CommandHandler("debug", debug_command))
    application.add_handler(CommandHandler("add_coins", add_coins_command))
    application.add_handler(CommandHandler("get_user", get_user_command))
    application.add_handler(CommandHandler("reset_user", reset_user_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("give_daily", give_daily_command))
    application.add_handler(CommandHandler("ban_user", ban_user_command))
    application.add_handler(CommandHandler("test_achievements", test_achievements_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("give_donate", give_donate_command))
    application.add_handler(CommandHandler("give_premium", give_premium_command))

    # Callbacks и сообщения
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_any_bet))

    # Платежи
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    # Фоновая задача напоминаний
    job_queue.run_repeating(send_reminders, interval=1800, first=60)

    print("✅ Бот запущен!")
    print(f"📊 Админы: {config.ADMIN_IDS}")
    print(f"💾 Файл данных: {config.DATA_FILE}")

    # Запуск бота
    application.run_polling()

main()
