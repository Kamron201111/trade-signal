"""
⚙️ Admin panel handleri
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.database import (
    get_all_users, get_pending_payments, approve_payment, 
    update_setting, get_setting, activate_premium
)
from config import ADMIN_IDS
import json

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Siz admin emassiz!")
        return
    
    await show_admin_menu(update, context)

async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = await get_all_users()
    pending = await get_pending_payments()
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💳 Kutilgan to'lovlar ({len(pending)})", callback_data="admin_payments")],
        [InlineKeyboardButton(f"👥 Foydalanuvchilar ({len(users)})", callback_data="admin_users")],
        [InlineKeyboardButton("💰 Narxlarni o'zgartirish", callback_data="admin_prices")],
        [InlineKeyboardButton("🏦 To'lov rekvizitlari", callback_data="admin_payment_info")],
        [InlineKeyboardButton("📊 Statistika", callback_data="admin_stats")],
    ])
    
    text = (
        f"⚙️ *Admin Panel*\n\n"
        f"👥 Jami foydalanuvchilar: *{len(users)}*\n"
        f"💳 Kutilayotgan to'lovlar: *{len(pending)}*\n\n"
        f"Nima qilmoqchisiz?"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

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
        await show_prices_editor(update, context)
    
    elif data == "admin_payment_info":
        await show_payment_info_editor(update, context)
    
    elif data == "admin_stats":
        await show_statistics(update, context)
    
    elif data.startswith("approve_"):
        parts = data.split("_")
        payment_id, user_id, plan = int(parts[1]), int(parts[2]), parts[3]
        await approve_payment_handler(update, context, payment_id, user_id, plan)
    
    elif data.startswith("reject_"):
        parts = data.split("_")
        payment_id, user_id = int(parts[1]), int(parts[2])
        await reject_payment_handler(update, context, payment_id, user_id)

async def show_pending_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payments = await get_pending_payments()
    
    if not payments:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Orqaga", callback_data="admin_menu")]])
        await update.callback_query.edit_message_text(
            "✅ Kutilayotgan to'lovlar yo'q!",
            reply_markup=keyboard
        )
        return
    
    text = f"💳 *Kutilayotgan to'lovlar ({len(payments)} ta):*\n\n"
    keyboard_buttons = []
    
    for p in payments[:10]:  # Eng ko'pi 10 ta
        plan_names = {"weekly": "Haftalik", "monthly": "Oylik", "quarterly": "3 Oylik"}
        text += f"#{p['id']} — User {p['user_id']} — {plan_names.get(p['plan'], p['plan'])} — ${p['amount']}\n"
        keyboard_buttons.append([
            InlineKeyboardButton(
                f"✅ #{p['id']} tasdiqlash", 
                callback_data=f"approve_{p['id']}_{p['user_id']}_{p['plan']}"
            ),
            InlineKeyboardButton(
                f"❌ Rad",
                callback_data=f"reject_{p['id']}_{p['user_id']}"
            )
        ])
    
    keyboard_buttons.append([InlineKeyboardButton("◀️ Orqaga", callback_data="admin_menu")])
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    
    await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

async def approve_payment_handler(update, context, payment_id: int, user_id: int, plan: str):
    await approve_payment(payment_id, plan, user_id)
    
    plan_names = {"weekly": "1 Haftalik", "monthly": "1 Oylik", "quarterly": "3 Oylik"}
    
    # Foydalanuvchiga xabar
    try:
        await update.get_bot().send_message(
            chat_id=user_id,
            text=(
                f"🎉 *Premium faollashtirildi!*\n\n"
                f"💎 Tarif: *{plan_names.get(plan, plan)}*\n\n"
                f"✅ Endi siz cheksiz signal olishingiz mumkin!\n"
                f"Xarid uchun rahmat! 🙏"
            ),
            parse_mode="Markdown"
        )
    except Exception:
        pass
    
    await update.callback_query.edit_message_caption(
        caption=f"✅ To'lov #{payment_id} tasdiqlandi! User {user_id} ga Premium berildi."
    )

async def reject_payment_handler(update, context, payment_id: int, user_id: int):
    from utils.database import DB_PATH
    import aiosqlite
    async with aiosqlite.connect(DB_PATH) as db:
        from datetime import datetime
        await db.execute(
            "UPDATE payment_requests SET status='rejected', processed_at=? WHERE id=?",
            (datetime.now().isoformat(), payment_id)
        )
        await db.commit()
    
    try:
        await update.get_bot().send_message(
            chat_id=user_id,
            text=(
                "❌ *To'lovingiz rad etildi.*\n\n"
                "Muammo bo'lsa, admin bilan bog'laning yoki qayta urinib ko'ring."
            ),
            parse_mode="Markdown"
        )
    except Exception:
        pass
    
    await update.callback_query.edit_message_caption(
        caption=f"❌ To'lov #{payment_id} rad etildi."
    )

async def show_prices_editor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prices = await get_setting("prices") or {}
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Haftalik: ${prices.get('weekly', 5)}", callback_data="edit_price_weekly")],
        [InlineKeyboardButton(f"Oylik: ${prices.get('monthly', 15)}", callback_data="edit_price_monthly")],
        [InlineKeyboardButton(f"3 Oylik: ${prices.get('quarterly', 35)}", callback_data="edit_price_quarterly")],
        [InlineKeyboardButton("◀️ Orqaga", callback_data="admin_menu")],
    ])
    
    await update.callback_query.edit_message_text(
        "💰 *Narxlarni o'zgartirish*\n\nO'zgartirmoqchi bo'lgan narxni tanlang:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def show_payment_info_editor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = await get_setting("payment") or {}
    
    text = (
        f"🏦 *Hozirgi to'lov ma'lumotlari:*\n\n"
        f"Karta: `{payment.get('card', 'N/A')}`\n"
        f"Egasi: {payment.get('name', 'N/A')}\n"
        f"Izoh: {payment.get('note', 'N/A')}\n\n"
        f"O'zgartirish uchun quyidagi formatda yozing:\n"
        f"`/setpayment karta|egasi|izoh`\n\n"
        f"Masalan:\n"
        f"`/setpayment 8600 1234 5678 9012|Alisher Karimov|TG username yozing`"
    )
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Orqaga", callback_data="admin_menu")]])
    await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = await get_all_users()
    premium_count = sum(1 for u in users if u['is_premium'])
    
    text = (
        f"👥 *Foydalanuvchilar*\n\n"
        f"Jami: {len(users)}\n"
        f"Premium: {premium_count}\n"
        f"Bepul: {len(users) - premium_count}\n\n"
        f"*So'nggi 10 ta:*\n"
    )
    
    for u in users[:10]:
        prem = "💎" if u['is_premium'] else "🆓"
        text += f"{prem} {u['full_name']} | @{u['username'] or 'N/A'}\n"
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Orqaga", callback_data="admin_menu")]])
    await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import aiosqlite
    from utils.database import DB_PATH
    
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM analyses") as cur:
            total_analyses = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM payment_requests WHERE status='approved'") as cur:
            total_paid = (await cur.fetchone())[0]
        async with db.execute("SELECT SUM(amount) FROM payment_requests WHERE status='approved'") as cur:
            total_revenue = (await cur.fetchone())[0] or 0
    
    text = (
        f"📊 *Statistika*\n\n"
        f"📈 Jami tahlillar: *{total_analyses}*\n"
        f"💳 Tasdiqlangan to'lovlar: *{total_paid}*\n"
        f"💰 Jami daromad: *${total_revenue:.2f}*\n"
    )
    
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Orqaga", callback_data="admin_menu")]])
    await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

# Admin buyruqlari
async def set_payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    try:
        args = " ".join(context.args).split("|")
        card, name, note = args[0].strip(), args[1].strip(), args[2].strip()
        await update_setting("payment", {"card": card, "name": name, "note": note})
        await update.message.reply_text("✅ To'lov ma'lumotlari yangilandi!")
    except Exception:
        await update.message.reply_text("❌ Format: `/setpayment karta|egasi|izoh`", parse_mode="Markdown")

async def set_price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    try:
        # /setprice weekly 7
        plan, amount = context.args[0], float(context.args[1])
        prices = await get_setting("prices") or {}
        prices[plan] = amount
        await update_setting("prices", prices)
        await update.message.reply_text(f"✅ {plan} narxi ${amount} ga o'zgartirildi!")
    except Exception:
        await update.message.reply_text("❌ Format: `/setprice weekly 7`", parse_mode="Markdown")

async def give_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    try:
        user_id, plan = int(context.args[0]), context.args[1]
        await activate_premium(user_id, plan)
        await update.message.reply_text(f"✅ User {user_id} ga {plan} Premium berildi!")
    except Exception:
        await update.message.reply_text("❌ Format: `/givepremium 123456 monthly`", parse_mode="Markdown")
