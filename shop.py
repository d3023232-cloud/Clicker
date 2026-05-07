"""Основные обработчики бота"""
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import config
import data_manager
from utils import get_user_name, is_premium_active, format_number
from game_logic import process_click, get_profile_text, get_top_text, process_daily_bonus
from shop import buy_upgrade, buy_title, get_shop_upgrades_keyboard, get_shop_titles_keyboard, get_donat_shop_keyboard
from minigames import validate_bet, start_crash_game, process_crash_game, start_roulette_game, process_roulette_game, start_duel_game, process_duel_game
from admin import is_admin, get_admin_panel_text, get_admin_keyboard, get_admin_command_description

def get_main_menu():
    """Главное меню с кнопками"""
    keyboard = [
        [InlineKeyboardButton("🏆 Топ", callback_data='top'),
         InlineKeyboardButton("🛒 Магазин", callback_data='shop')],
        [InlineKeyboardButton("🎮 Мини-игры", callback_data='minigames'),
         InlineKeyboardButton("🎁 Ежедневный бонус", callback_data='daily')],
        [InlineKeyboardButton("💎 Donat-магазин", callback_data='donat_shop'),
         InlineKeyboardButton("🤝 Рефералка", callback_data='referral')],
        [InlineKeyboardButton("🏅 Достижения", callback_data='achievements'),
         InlineKeyboardButton("👤 Мой профиль", callback_data='my_profile')],
        [InlineKeyboardButton("🖱 Клик!", callback_data='click')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    data_manager.update_user_name(user_id, get_user_name(user))

    # Реферальная система
    if context.args and context.args[0].startswith('ref'):
        try:
            referrer_id = int(context.args[0][3:])
            if referrer_id != user_id and data_manager.user_data[user_id]["referrer_id"] is None:
                data_manager.user_data[user_id]["referrer_id"] = referrer_id
                data_manager.user_data[referrer_id]["donate_coins"] += 2
                data_manager.save_data()
                try:
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text="🎁 Вы получили 2 Donat-коина за приглашённого друга!"
                    )
                except:
                    pass
        except:
            pass

    data_manager.save_data()

    from utils import get_time_greeting
    greeting = get_time_greeting()
    ref_link = f"https://t.me/{config.YOUR_BOT_USERNAME}?start=ref{user_id}"

    await update.message.reply_text(
        f"{greeting}
"
        f"🎮 Добро пожаловать в Clicker Bot!

"
        f"🔗 Ваша реферальная ссылка:
<code>{ref_link}</code>",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = user.id
    data_manager.update_user_name(user_id, get_user_name(user))

    # Админ-панель кнопки
    if query.data.startswith('admin_cmd_'):
        cmd = query.data[10:]
        desc = get_admin_command_description(cmd)
        await query.answer(desc, show_alert=True)
        return

    # === ГЛАВНОЕ МЕНЮ ===
    if query.data == 'click':
        result = process_click(user_id)

        ach_msg = ""
        if result["new_achievements"]:
            ach_names = [config.ACHIEVEMENTS[aid]["name"] for aid in result["new_achievements"]]
            ach_msg = "

🎉 Новое достижение: " + ", ".join(ach_names) + "!"

        text = (
            f"🖱 Вы кликнули!
"
            f"💰 +{format_number(int(result['coins_earned']))} монет от клика
"
            f"🤖 +{format_number(int(result['auto_income']))} монет от автокликера
"
            f"🪙 Всего монет: {format_number(int(result['total_coins']))}
"
            f"⚡ Сила клика: {result['click_power']}"
            + ach_msg
        )
        await query.edit_message_text(text=text, reply_markup=get_main_menu())

    elif query.data == 'top':
        await query.edit_message_text(text=get_top_text(), reply_markup=get_main_menu())

    elif query.data == 'shop':
        keyboard = [
            [InlineKeyboardButton("🔧 Улучшения", callback_data='shop_upgrades')],
            [InlineKeyboardButton("🏅 Звания", callback_data='shop_titles')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='back')]
        ]
        await query.edit_message_text("🛒 Магазин:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'shop_upgrades':
        keyboard = get_shop_upgrades_keyboard(user_id)
        await query.edit_message_text("🔧 Улучшения:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'shop_titles':
        keyboard = get_shop_titles_keyboard(user_id)
        await query.edit_message_text("🏅 Звания (покупаются за монеты):", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'daily':
        result = process_daily_bonus(user_id)
        if result["success"]:
            await query.edit_message_text(
                f"🎁 Получено {format_number(result['bonus'])} монет!
Возвращайтесь завтра!",
                reply_markup=get_main_menu()
            )
        else:
            await query.edit_message_text(
                f"🎁 Бонус можно получить через {result['hours_left']} ч.",
                reply_markup=get_main_menu()
            )

    elif query.data == 'achievements':
        ud = data_manager.user_data[user_id]
        msg = "🏅 Ваши достижения:
"
        for key, ach in config.ACHIEVEMENTS.items():
            status = "✅" if key in ud["achievements"] else "❌"
            msg += f"{status} {ach['name']} — {ach['desc']}
"
        msg += f"
👑 Ваше звание: {ud['title']}"
        await query.edit_message_text(msg, reply_markup=get_main_menu())

    elif query.data == 'my_profile':
        msg = get_profile_text(user_id)
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=get_main_menu())

    elif query.data == 'referral':
        ref_link = f"https://t.me/{config.YOUR_BOT_USERNAME}?start=ref{user_id}"
        ud = data_manager.user_data[user_id]
        ref_count = len([u for u in data_manager.user_data.values() if u.get("referrer_id") == user_id])
        msg = (
            f"🤝 <b>Реферальная система</b>

"
            f"🔗 Ваша ссылка:
<code>{ref_link}</code>

"
            f"👥 Приглашено: <b>{ref_count}</b> друзей
"
            f"💎 За каждого: <b>2 Donat-коина</b>
"
            f"💰 Всего получено: <b>{ud['donate_coins']}</b> Donat-коинов"
        )
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=get_main_menu())

    elif query.data == 'donat_shop':
        keyboard = get_donat_shop_keyboard()
        await query.edit_message_text(
            "💎 <b>Donat-магазин (оплата звёздами)</b>
Покупайте за ⭐:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith('buy_stars_'):
        item_key = query.data[10:]
        if item_key not in config.DONAT_SHOP:
            await query.edit_message_text("❌ Товар не найден.", reply_markup=get_main_menu())
            return

        item = config.DONAT_SHOP[item_key]
        try:
            from telegram import LabeledPrice
            await context.bot.send_invoice(
                chat_id=user_id,
                title=item['name'],
                description=item['desc'],
                payload=f"donat_{item_key}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="Цена", amount=item['stars'])],
                max_tip_amount=0,
                suggested_tip_amounts=[],
                start_parameter="buy"
            )
        except Exception as e:
            print(f"❌ Ошибка при отправке инвойса: {e}")
            await query.edit_message_text("❌ Ошибка при создании инвойса.", reply_markup=get_main_menu())

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
        result = start_crash_game(user_id)
        if not result["success"]:
            await query.answer(result["message"], show_alert=True)
            return

        msg = (
            "💥 <b>Краш-игра</b>
"
            "Ставка от 20 до 1 000 000 монет.

"
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

            result = process_crash_game(user_id, bet, multiplier)

            if not result["success"]:
                await query.edit_message_text(result["message"], reply_markup=get_main_menu())
                return

            await query.edit_message_text(result["message"], parse_mode="HTML", reply_markup=get_main_menu())

            context.user_data.pop("crash_state", None)
            context.user_data.pop("crash_bet", None)
            context.user_data.pop("crash_user_id", None)
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {e}", reply_markup=get_main_menu())

    # === РУЛЕТКА ===
    elif query.data == 'game_roulette_start':
        result = start_roulette_game(user_id)
        if not result["success"]:
            await query.answer(result["message"], show_alert=True)
            return

        msg = (
            "🎰 <b>Рулетка</b>
"
            "Ставка от 20 до 1 000 000 монет.
"
            "Выберите цвет:
"
            "• 🔴 Красное (×1.9)
"
            "• ⚫ Чёрное (×1.9)
"
            "• 🟢 Зелёное (×9.0, шанс 10%)

"
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

        result = process_roulette_game(user_id, bet, color)

        if not result["success"]:
            await query.edit_message_text(result["message"], reply_markup=get_main_menu())
            return

        await query.edit_message_text(
            f"🎰 <b>Рулетка</b>
{result['message']}

🪙 Баланс: {format_number(int(result['balance']))}",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )

        context.user_data.pop("roulette_state", None)
        context.user_data.pop("roulette_bet", None)
        context.user_data.pop("roulette_user_id", None)

    # === ДУЭЛЬ ===
    elif query.data == 'game_duel_start':
        result = start_duel_game(user_id)
        if not result["success"]:
            await query.answer(result["message"], show_alert=True)
            return

        msg = (
            "⚔️ <b>Дуэль с ботом</b>
"
            "Ставка от 100 до 1 000 000 монет.
"
            "Шанс победы: 48% (бот берёт 4% комиссии).

"
            "<i>Введите ставку в чат</i>"
        )
        await query.edit_message_text(msg, parse_mode="HTML")
        context.user_data["duel_state"] = "bet"
        context.user_data["duel_user_id"] = user_id

    # === ПОКУПКИ ===
    elif query.data.startswith('buy_upg_'):
        upg_key = query.data[8:]
        result = buy_upgrade(user_id, upg_key)

        if result["success"]:
            if result.get("new_achievement"):
                await query.answer("🎉 Открыто достижение: Робо-помощник!", show_alert=True)
            await query.edit_message_text(result["message"], reply_markup=get_main_menu())
        else:
            await query.answer(result["message"], show_alert=True)

    elif query.data.startswith('buy_title_'):
        title_key = query.data[11:]
        result = buy_title(user_id, title_key)

        if result["success"]:
            await query.edit_message_text(result["message"], reply_markup=get_main_menu())
        else:
            await query.answer(result["message"], show_alert=True)

    elif query.data == 'back' or query.data == 'noop':
        await query.edit_message_text("🎮 Главное меню:", reply_markup=get_main_menu())

async def mm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /mm (мой профиль)"""
    user_id = update.effective_user.id
    data_manager.update_user_name(user_id, get_user_name(update.effective_user))
    msg = get_profile_text(user_id)
    await update.message.reply_text(msg, parse_mode="HTML")

async def admins_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /admins"""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return

    from telegram import InlineKeyboardMarkup
    keyboard = get_admin_keyboard()
    msg = get_admin_panel_text()

    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
