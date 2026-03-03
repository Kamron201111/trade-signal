import os
import json
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.database import get_all_users, get_pending_payments, approve_payment, update_setting, get_setting, activate_premium, DB_PATH

ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "123456789").split(",")))

def is_admin(user_id):
    return user_id in ADMIN_IDS

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Siz admin emassiz!")
        return
    await show_admin_menu(update, context)

async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = await get_all_users()
    pending = await get_pending_payments()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Kutilgan to'lovlar (" + str(len(pending)) + ")", callback_data="admin_payments")],
        [InlineKeyboardButton("Foydalanuvchilar (" + str(len(users)) + ")", callback_data="admin_users")],
        [InlineKeyboardButton("Narxlarni o'zgartirish", callback_data="admin_prices")],
        [InlineKeyboardButton("To'lov rekvizitlari", callback_data="admin_payment_info")],
        [InlineKeyboardButton("Statistika", callback_data="admin_stats")],
    ])
    text = "Admin Panel\n\nFoydalanuvchilar: " + str(len(users)) + "\nKutilgan to'lovlar: " + str(len(pending))
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text, reply_markup=keyboard)

async def handle_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    data = query.data
    if data == "admin_menu":
        await show_admin_menu(update, context)
    elif data == "admin_payments":
        await show_pending_payments(update, context)
    elif data == "admin_users":
        await show_users(update, context)
    elif data == "admin_prices":
        await show_prices(update, context)
    elif data == "admin_payment_info":
        await show_payment_info(update, context)
    elif data == "admin_stats":
        await show_stats(update, context)
    elif data.startswith("approve_"):
        parts = data.split("_")
        await do_approve(update, int(parts[1]), int(parts[2]), parts[3])
    elif data.startswith("reject_"):
        parts = data.split("_")
        await do_reject(update, int(parts[1]), int(parts[2]))

async def show_pending_payments(update, context):
    payments = await get_pending_payments()
    if not payments:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="admin_menu")]])
        await update.callback_query.edit_message_text("Kutilgan to'lovlar yo'q!", reply_markup=keyboard)
        return
    text = "Kutilgan to'lovlar:\n\n"
    buttons = []
    for p in payments[:10]:
        text += "#" + str(p["id"]) + " — " + str(p["user_id"]) + " — " + p["plan"] + " — $" + str(p["amount"]) + "\n"
        buttons.append([
            InlineKeyboardButton("✅ #" + str(p["id"]), callback_data="approve_" + str(p["id"]) + "_" + str(p["user_id"]) + "_" + p["plan"]),
            InlineKeyboardButton("❌ Rad", callback_data="reject_" + str(p["id"]) + "_" + str(p["user_id"])),
        ])
    buttons.append([InlineKeyboardButton("Orqaga", callback_data="admin_menu")])
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def do_approve(update, payment_id, user_id, plan):
    await approve_payment(payment_id, plan, user_id)
    plan_names = {"weekly": "1 Haftalik", "monthly": "1 Oylik", "quarterly": "3 Oylik"}
    try:
        await update.get_bot().send_message(
            chat_id=user_id,
            text="Premium faollashtirildi!\nTarif: " + plan_names.get(plan, plan) + "\nRahmat!"
        )
    except Exception:
        pass
    await update.callback_query.edit_message_caption(caption="To'lov #" + str(payment_id) + " tasdiqlandi!")

async def do_reject(update, payment_id, user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE payment_requests SET status='rejected', processed_at=? WHERE id=?", (datetime.now().isoformat(), payment_id))
    conn.commit()
    conn.close()
    try:
        await update.get_bot().send_message(chat_id=user_id, text="To'lovingiz rad etildi. Muammo bo'lsa qayta urinib ko'ring.")
    except Exception:
        pass
    await update.callback_query.edit_message_caption(caption="To'lov #" + str(payment_id) + " rad etildi.")

async def show_prices(update, context):
    prices = await get_setting("prices") or {}
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="admin_menu")]])
    text = (
        "Narxlarni o'zgartirish uchun yozing:\n\n"
        "/setprice weekly 7\n"
        "/setprice monthly 20\n"
        "/setprice quarterly 40\n\n"
        "Hozirgi narxlar:\n"
        "Haftalik: $" + str(prices.get("weekly", 5)) + "\n"
        "Oylik: $" + str(prices.get("monthly", 15)) + "\n"
        "3 Oylik: $" + str(prices.get("quarterly", 35))
    )
    await update.callback_query.edit_message_text(text, reply_markup=keyboard)

async def show_payment_info(update, context):
    payment = await get_setting("payment") or {}
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="admin_menu")]])
    text = (
        "To'lov ma'lumotlari:\n\n"
        "Karta: " + payment.get("card", "---") + "\n"
        "Egasi: " + payment.get("name", "---") + "\n\n"
        "O'zgartirish:\n"
        "/setpayment 8600123456789012|Ism Familiya|Izoh"
    )
    await update.callback_query.edit_message_text(text, reply_markup=keyboard)

async def show_users(update, context):
    users = await get_all_users()
    premium_count = sum(1 for u in users if u["is_premium"])
    text = "Foydalanuvchilar\n\nJami: " + str(len(users)) + "\nPremium: " + str(premium_count) + "\nBepul: " + str(len(users) - premium_count) + "\n\nSo'nggi 10:\n"
    for u in users[:10]:
        mark = "💎" if u["is_premium"] else "👤"
        text += mark + " " + u["full_name"] + "\n"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="admin_menu")]])
    await update.callback_query.edit_message_text(text, reply_markup=keyboard)

async def show_stats(update, context):
    conn = sqlite3.connect(DB_PATH)
    total_a = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
    total_p = conn.execute("SELECT COUNT(*) FROM payment_requests WHERE status='approved'").fetchone()[0]
    total_r = conn.execute("SELECT SUM(amount) FROM payment_requests WHERE status='approved'").fetchone()[0] or 0
    conn.close()
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="admin_menu")]])
    await update.callback_query.edit_message_text(
        "Statistika\n\nTahlillar: " + str(total_a) + "\nTasdiqlangan to'lovlar: " + str(total_p) + "\nDaromad: $" + str(round(total_r, 2)),
        reply_markup=keyboard
    )

async def set_payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    try:
        args = " ".join(context.args).split("|")
        card, name, note = args[0].strip(), args[1].strip(), args[2].strip()
        await update_setting("payment", {"card": card, "name": name, "note": note, "confirm_time": "1-2 soat"})
        await update.message.reply_text("To'lov ma'lumotlari yangilandi!")
    except Exception:
        await update.message.reply_text("Format: /setpayment karta|egasi|izoh")

async def set_price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    try:
        plan, amount = context.args[0], float(context.args[1])
        prices = await get_setting("prices") or {}
        prices[plan] = amount
        await update_setting("prices", prices)
        await update.message.reply_text(plan + " narxi $" + str(amount) + " ga o'zgartirildi!")
    except Exception:
        await update.message.reply_text("Format: /setprice weekly 7")

async def give_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    try:
        user_id, plan = int(context.args[0]), context.args[1]
        await activate_premium(user_id, plan)
        await update.message.reply_text(str(user_id) + " ga " + plan + " Premium berildi!")
    except Exception:
        await update.message.reply_text("Format: /givepremium 123456 monthly")
