import os, sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.database import (
    db_get_all_users, db_get_pending, db_approve_payment, db_reject_payment,
    db_set_setting, db_get_setting, db_activate_premium, db_get_stats, DB_PATH
)

ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "123456789").split(",")))
PLAN_NAMES = {"weekly": "1 Haftalik", "monthly": "1 Oylik", "quarterly": "3 Oylik"}

def is_admin(uid):
    return uid in ADMIN_IDS

async def cmd_admin(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Ruxsat yo'q!")
        return
    await show_admin_menu(update, context)

async def show_admin_menu(update, context):
    users = db_get_all_users()
    pending = db_get_pending()
    stats = db_get_stats()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 To'lovlar (" + str(len(pending)) + ")", callback_data="adm_payments")],
        [InlineKeyboardButton("👥 Foydalanuvchilar (" + str(len(users)) + ")", callback_data="adm_users")],
        [InlineKeyboardButton("💰 Narxlar", callback_data="adm_prices"),
         InlineKeyboardButton("🏦 Karta", callback_data="adm_card")],
        [InlineKeyboardButton("📊 Statistika", callback_data="adm_stats")],
        [InlineKeyboardButton("📢 Xabar yuborish", callback_data="adm_broadcast")],
    ])
    text = (
        "Admin Panel\n\n"
        "Foydalanuvchilar: " + str(stats["total_users"]) + "\n"
        "Premium: " + str(stats["premium_users"]) + "\n"
        "Tahlillar: " + str(stats["total_analyses"]) + "\n"
        "Kutilgan to'lovlar: " + str(len(pending)) + "\n"
        "Jami daromad: " + str(stats["revenue"]) + " so'm"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb)
    else:
        await update.message.reply_text(text, reply_markup=kb)

async def adm_callback(update, context):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return
    data = query.data

    if data == "adm_menu":
        await show_admin_menu(update, context)
    elif data == "adm_payments":
        await show_payments(update, context)
    elif data == "adm_users":
        await show_users(update, context)
    elif data == "adm_prices":
        await show_prices(update, context)
    elif data == "adm_card":
        await show_card(update, context)
    elif data == "adm_stats":
        await show_stats(update, context)
    elif data == "adm_broadcast":
        await show_broadcast(update, context)
    elif data.startswith("appr_"):
        parts = data.split("_")
        pid, uid, plan = int(parts[1]), int(parts[2]), parts[3]
        await do_approve(update, context, pid, uid, plan)
    elif data.startswith("rejt_"):
        parts = data.split("_")
        pid, uid = int(parts[1]), int(parts[2])
        await do_reject(update, context, pid, uid)

async def show_payments(update, context):
    payments = db_get_pending()
    kb_rows = []
    if not payments:
        text = "Kutilgan to'lovlar yo'q!"
    else:
        text = "Kutilgan to'lovlar:\n\n"
        for p in payments[:8]:
            text += "#" + str(p["id"]) + " | " + str(p["user_id"]) + " | " + PLAN_NAMES.get(p["plan"],p["plan"]) + " | " + str(p["amount"]) + " so'm\n"
            kb_rows.append([
                InlineKeyboardButton("✅ #" + str(p["id"]), callback_data="appr_" + str(p["id"]) + "_" + str(p["user_id"]) + "_" + p["plan"]),
                InlineKeyboardButton("❌ Rad", callback_data="rejt_" + str(p["id"]) + "_" + str(p["user_id"])),
            ])
    kb_rows.append([InlineKeyboardButton("Orqaga", callback_data="adm_menu")])
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb_rows))

async def do_approve(update, context, pid, uid, plan):
    db_approve_payment(pid, plan, uid)
    try:
        await update.get_bot().send_message(
            chat_id=uid,
            text="Premium faollashtirildi! 🎉\nTarif: " + PLAN_NAMES.get(plan, plan) + "\nRahmat!"
        )
    except Exception:
        pass
    try:
        await update.callback_query.edit_message_caption(caption="✅ #" + str(pid) + " tasdiqlandi!")
    except Exception:
        await update.callback_query.edit_message_text("✅ #" + str(pid) + " tasdiqlandi!")

async def do_reject(update, context, pid, uid):
    db_reject_payment(pid)
    try:
        await update.get_bot().send_message(chat_id=uid, text="To'lovingiz rad etildi. Muammo bo'lsa qayta urinib ko'ring.")
    except Exception:
        pass
    try:
        await update.callback_query.edit_message_caption(caption="❌ #" + str(pid) + " rad etildi.")
    except Exception:
        await update.callback_query.edit_message_text("❌ #" + str(pid) + " rad etildi.")

async def show_users(update, context):
    users = db_get_all_users()
    text = "Foydalanuvchilar (" + str(len(users)) + " ta)\n\n"
    for u in users[:15]:
        mark = "💎" if u["is_premium"] else "👤"
        text += mark + " " + u["full_name"] + " | @" + (u["username"] or "N/A") + "\n"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="adm_menu")]])
    await update.callback_query.edit_message_text(text, reply_markup=kb)

async def show_prices(update, context):
    prices = db_get_setting("prices") or {}
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="adm_menu")]])
    await update.callback_query.edit_message_text(
        "Narxlar (so'mda):\n\n"
        "Haftalik: " + str(prices.get("weekly", 50000)) + "\n"
        "Oylik: " + str(prices.get("monthly", 150000)) + "\n"
        "3 Oylik: " + str(prices.get("quarterly", 350000)) + "\n\n"
        "O'zgartirish uchun:\n"
        "/setprice weekly 70000\n"
        "/setprice monthly 200000\n"
        "/setprice quarterly 500000",
        reply_markup=kb
    )

async def show_card(update, context):
    payment = db_get_setting("payment") or {}
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="adm_menu")]])
    await update.callback_query.edit_message_text(
        "Karta ma'lumotlari:\n\n"
        "Karta: " + payment.get("card", "---") + "\n"
        "Egasi: " + payment.get("name", "---") + "\n"
        "Izoh: " + payment.get("note", "---") + "\n\n"
        "O'zgartirish:\n"
        "/setcard 8600123456789012|Ism Familiya|Izohingiz",
        reply_markup=kb
    )

async def show_stats(update, context):
    s = db_get_stats()
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="adm_menu")]])
    await update.callback_query.edit_message_text(
        "Statistika\n\n"
        "Jami foydalanuvchilar: " + str(s["total_users"]) + "\n"
        "Premium: " + str(s["premium_users"]) + "\n"
        "Bepul: " + str(s["total_users"] - s["premium_users"]) + "\n"
        "Jami tahlillar: " + str(s["total_analyses"]) + "\n"
        "Tasdiqlangan to'lovlar: " + str(s["approved_payments"]) + "\n"
        "Jami daromad: " + str(s["revenue"]) + " so'm",
        reply_markup=kb
    )

async def show_broadcast(update, context):
    context.user_data["broadcast_mode"] = True
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Bekor qilish", callback_data="adm_menu")]])
    await update.callback_query.edit_message_text(
        "Barcha foydalanuvchilarga xabar yuboring.\n\n"
        "Xabar matnini yozing:",
        reply_markup=kb
    )

async def handle_broadcast(update, context):
    if not is_admin(update.effective_user.id):
        return
    if not context.user_data.get("broadcast_mode"):
        return
    context.user_data["broadcast_mode"] = False
    text = update.message.text
    users = db_get_all_users()
    sent, failed = 0, 0
    for u in users:
        try:
            await update.get_bot().send_message(chat_id=u["user_id"], text=text)
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(
        "Xabar yuborildi!\n\nYuborildi: " + str(sent) + "\nXato: " + str(failed)
    )

async def cmd_setprice(update, context):
    if not is_admin(update.effective_user.id):
        return
    try:
        plan, amount = context.args[0], int(context.args[1])
        prices = db_get_setting("prices") or {}
        prices[plan] = amount
        db_set_setting("prices", prices)
        await update.message.reply_text(plan + " = " + str(amount) + " so'm qilindi!")
    except Exception:
        await update.message.reply_text("Format: /setprice weekly 70000")

async def cmd_setcard(update, context):
    if not is_admin(update.effective_user.id):
        return
    try:
        parts = " ".join(context.args).split("|")
        db_set_setting("payment", {
            "card": parts[0].strip(),
            "name": parts[1].strip(),
            "note": parts[2].strip(),
            "confirm_time": "1-2 soat"
        })
        await update.message.reply_text("Karta ma'lumotlari yangilandi!")
    except Exception:
        await update.message.reply_text("Format: /setcard 8600...|Ism|Izoh")

async def cmd_giveprem(update, context):
    if not is_admin(update.effective_user.id):
        return
    try:
        uid, plan = int(context.args[0]), context.args[1]
        db_activate_premium(uid, plan)
        await update.message.reply_text(str(uid) + " ga " + plan + " Premium berildi!")
        await update.get_bot().send_message(chat_id=uid, text="Premium faollashtirildi! 🎉\nTarif: " + PLAN_NAMES.get(plan,plan))
    except Exception:
        await update.message.reply_text("Format: /giveprem 123456789 monthly")

async def cmd_ban(update, context):
    if not is_admin(update.effective_user.id):
        return
    try:
        uid = int(context.args[0])
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (uid,))
        conn.commit()
        conn.close()
        await update.message.reply_text(str(uid) + " ban qilindi!")
    except Exception:
        await update.message.reply_text("Format: /ban 123456789")
