from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.database import db_get_setting, db_save_payment, db_get_user, db_is_premium
import os

ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "123456789").split(",")))
PLAN_NAMES = {"weekly": "1 Haftalik", "monthly": "1 Oylik", "quarterly": "3 Oylik"}

async def premium_info(update, context):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    prem = db_is_premium(user_id)
    prices = db_get_setting("prices") or {"weekly": 50000, "monthly": 150000, "quarterly": 350000}
    status = "Sizda hozir Premium bor!\n\n" if prem else ""
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("1 Haftalik — " + str(prices["weekly"]) + " so'm", callback_data="buy_weekly")],
        [InlineKeyboardButton("1 Oylik — " + str(prices["monthly"]) + " so'm", callback_data="buy_monthly")],
        [InlineKeyboardButton("3 Oylik — " + str(prices["quarterly"]) + " so'm", callback_data="buy_quarterly")],
        [InlineKeyboardButton("Orqaga", callback_data="main_menu")],
    ])
    await query.edit_message_text(
        status +
        "💎 Premium Obuna\n\n"
        "Premium afzalliklari:\n"
        "✅ Kuniga cheksiz tahlil\n"
        "✅ 100 ta Forex va Crypto juftlik\n"
        "✅ Barcha 10 ta strategiya\n"
        "✅ Strategiyani o'zing tanlash\n"
        "✅ Aniq risk menejment\n\n"
        "Tarif tanlang:",
        reply_markup=kb
    )

async def buy_plan(update, context):
    query = update.callback_query
    await query.answer()
    plan = query.data.replace("buy_", "")
    prices = db_get_setting("prices") or {"weekly": 50000, "monthly": 150000, "quarterly": 350000}
    payment = db_get_setting("payment") or {}
    amount = prices.get(plan, 0)
    context.user_data["pending_plan"] = plan
    context.user_data["pending_amount"] = amount
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="premium_info")]])
    await query.edit_message_text(
        "💳 To'lov ma'lumotlari\n\n"
        "Tarif: " + PLAN_NAMES.get(plan, plan) + "\n"
        "Summa: " + str(amount) + " so'm\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Karta raqami:\n" + payment.get("card", "---") + "\n\n"
        "Karta egasi:\n" + payment.get("name", "---") + "\n\n"
        "Izoh: " + payment.get("note", "---") + "\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "To'lovni amalga oshirib,\n"
        "screenshot yuboring!",
        reply_markup=kb
    )

async def handle_payment_photo(update, context):
    user_id = update.effective_user.id
    user = db_get_user(user_id)
    if not user:
        return
    plan = context.user_data.get("pending_plan")
    amount = context.user_data.get("pending_amount", 0)
    if not plan:
        return
    file_id = update.message.photo[-1].file_id
    pid = db_save_payment(user_id, plan, amount, file_id)
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Tasdiqlash", callback_data="appr_" + str(pid) + "_" + str(user_id) + "_" + plan),
        InlineKeyboardButton("❌ Rad etish", callback_data="rejt_" + str(pid) + "_" + str(user_id)),
    ]])
    caption = (
        "Yangi to'lov so'rovi!\n\n"
        "Ism: " + user["full_name"] + "\n"
        "Tel: " + user["phone"] + "\n"
        "ID: " + str(user_id) + "\n"
        "Tarif: " + PLAN_NAMES.get(plan, plan) + "\n"
        "Summa: " + str(amount) + " so'm\n"
        "So'rov ID: #" + str(pid)
    )
    for admin_id in ADMIN_IDS:
        try:
            await update.get_bot().send_photo(chat_id=admin_id, photo=file_id, caption=caption, reply_markup=kb)
        except Exception:
            pass
    context.user_data.pop("pending_plan", None)
    context.user_data.pop("pending_amount", None)
    await update.message.reply_text(
        "To'lov screenshoti qabul qilindi! ✅\n\n"
        "So'rov ID: #" + str(pid) + "\n\n"
        "Admin " + str(db_get_setting("payment") and db_get_setting("payment").get("confirm_time","1-2 soat") or "1-2 soat") + " ichida tekshiradi.\nRahmat!"
    )
