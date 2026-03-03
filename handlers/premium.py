from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.database import get_setting, save_payment_request, get_user, is_premium
from config import ADMIN_IDS

async def premium_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "premium_info":
        await show_premium_plans(update, context)
    elif data.startswith("premium_buy_"):
        plan = data.replace("premium_buy_", "")
        await show_payment_details(update, context, plan)
    elif data == "main_menu":
        from handlers.start import show_main_menu
        user = await get_user(update.effective_user.id)
        await show_main_menu(update, context, user["full_name"] if user else "")

async def show_premium_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prices = await get_setting("prices") or {"weekly": 5, "monthly": 15, "quarterly": 35}
    is_prem = await is_premium(update.effective_user.id)
    status = "💎 Sizda Premium mavjud!\n\n" if is_prem else ""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 1 Haftalik — $" + str(prices["weekly"]), callback_data="premium_buy_weekly")],
        [InlineKeyboardButton("📆 1 Oylik — $" + str(prices["monthly"]), callback_data="premium_buy_monthly")],
        [InlineKeyboardButton("🗓 3 Oylik — $" + str(prices["quarterly"]), callback_data="premium_buy_quarterly")],
        [InlineKeyboardButton("🏠 Orqaga", callback_data="main_menu")],
    ])
    text = (
        status +
        "💎 Premium Obuna\n\n"
        "Premium bilan:\n"
        "✅ Cheksiz kunlik signal\n"
        "✅ 100 ta juftlik tahlili\n"
        "✅ Barcha strategiyalar\n\n"
        "Narxlar:"
    )
    await update.callback_query.edit_message_text(text, reply_markup=keyboard)

async def show_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE, plan: str):
    prices = await get_setting("prices") or {"weekly": 5, "monthly": 15, "quarterly": 35}
    payment = await get_setting("payment") or {}
    plan_names = {"weekly": "1 Haftalik", "monthly": "1 Oylik", "quarterly": "3 Oylik"}
    amount = prices.get(plan, 0)
    context.user_data["pending_plan"] = plan
    context.user_data["pending_amount"] = amount
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Orqaga", callback_data="premium_info")],
    ])
    card = payment.get("card", "Noma lum")
    name = payment.get("name", "")
    note = payment.get("note", "")
    confirm_time = payment.get("confirm_time", "1-2 soat")
    text = (
        "💳 To'lov ma'lumotlari\n\n"
        "Tarif: " + plan_names.get(plan, plan) + "\n"
        "Summa: $" + str(amount) + "\n\n"
        "Karta: " + card + "\n"
        "Egasi: " + name + "\n"
        "Izoh: " + note + "\n\n"
        "To'lovdan so'ng screenshotni yuboring.\n"
        "Admin " + confirm_time + " ichida tasdiqlaydi."
    )
    await update.callback_query.edit_message_text(text, reply_markup=keyboard)

async def handle_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await update.message.reply_text("Avval /start bosing!")
        return
    plan = context.user_data.get("pending_plan")
    amount = context.user_data.get("pending_amount", 0)
    if not plan:
        return
    photo = update.message.photo[-1]
    file_id = photo.file_id
    payment_id = await save_payment_request(user_id, plan, amount, file_id)
    plan_names = {"weekly": "1 Haftalik", "monthly": "1 Oylik", "quarterly": "3 Oylik"}
    admin_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Tasdiqlash", callback_data="approve_" + str(payment_id) + "_" + str(user_id) + "_" + plan),
            InlineKeyboardButton("❌ Rad etish", callback_data="reject_" + str(payment_id) + "_" + str(user_id)),
        ]
    ])
    admin_text = (
        "💳 Yangi to'lov!\n\n"
        "Ism: " + user["full_name"] + "\n"
        "Tel: " + user["phone"] + "\n"
        "ID: " + str(user_id) + "\n"
        "Tarif: " + plan_names.get(plan, plan) + "\n"
        "Summa: $" + str(amount) + "\n"
        "To'lov ID: #" + str(payment_id)
    )
    for admin_id in ADMIN_IDS:
        try:
            await update.get_bot().send_photo(
                chat_id=admin_id,
                photo=file_id,
                caption=admin_text,
                reply_markup=admin_keyboard
            )
        except Exception:
            pass
    context.user_data.pop("pending_plan", None)
    context.user_data.pop("pending_amount", None)
    await update.message.reply_text(
        "✅ To'lov screenshoti qabul qilindi!\n\n"
        "So'rov ID: #" + str(payment_id) + "\n\n"
        "Admin tez orada tekshiradi. Rahmat!"
    )
