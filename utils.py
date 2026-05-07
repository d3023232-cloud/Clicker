"""Обработка платежей Telegram Stars"""
import config
import data_manager
from game_logic import update_league

async def pre_checkout_handler(update, context):
    """Обработчик предварительной проверки платежа"""
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment_handler(update, context):
    """Обработчик успешного платежа"""
    user_id = update.effective_user.id
    successful_payment = update.message.successful_payment
    payload = successful_payment.invoice_payload

    if payload.startswith("donat_"):
        item_key = payload[6:]
        if item_key in config.DONAT_SHOP:
            item = config.DONAT_SHOP[item_key]
            # Начисляем Donat-коины
            data_manager.user_data[user_id]["donate_coins"] += item["cost"]
            data_manager.save_data()

            await update.message.reply_text(
                f"✅ Оплата прошла успешно!
"
                f"Вы получили: <b>{item['name']}</b> ({item['cost']} 💎)",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text("❌ Неизвестный товар.")
    else:
        await update.message.reply_text("❌ Неизвестный платеж.")
