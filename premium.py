"""
💎 Premium obuna handleri
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
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
        await show_main_menu(update, context, user['full_name'] if user else "")

async def show_premium_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prices = await get_setting("prices") or {"weekly": 5, "monthly": 15, "quarterly": 35}
    
    is_prem = await is_premium(update.effective_user.id)
    status = "💎 *Sizda Premium mavjud!*\n\n" if is_prem else ""
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"📅 1 Haftalik — ${prices['weekly']}", 
            callback_data="premium_buy_weekly"
        )],
        [InlineKeyboardButton(
            f"📆 1 Oylik — ${prices['monthly']}", 
            callback_data="premium_buy_monthly"
        )],
        [InlineKeyboardButton(
            f"🗓 3 Oylik — ${prices['quarterly']} (eng foydali!)", 
            callback_data="premium_buy_quarterly"
        )],
        [InlineKeyboardButton("🏠 Orqaga", callback_data="main_menu")],
    ])
    
    text = (
        f"{status}"
        f"💎 *Premium Obuna*\n\n"
        f"Premium bilan qo'shimcha imkoniyatlar:\n\n"
        f"✅ Cheksiz kunlik signal\n"
        f"✅ 100 ta juftlik tahlili\n"
        f"✅ Tezkor signal (priority)\n"
        f"✅ Risk menejment tavsiyalari\n"
        f"✅ Barcha strategiyalar\n\n"
        f"💰 *Narxlar:*"
    )
    
    await update.callback_query.edit_message_text(
        text, parse_mode="Markdown", reply_markup=keyboard
    )

async def show_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE, plan: str):
    prices = await get_setting("prices") or {"weekly": 5, "monthly": 15, "quarterly": 35}
    payment = await get_setting("payment") or {}
    
    plan_names = {"weekly": "1 Haftalik", "monthly": "1 Oylik", "quarterly": "3 Oylik"}
    amount = prices.get(plan, 0)
    
    context.user_data['pending_plan'] = plan
    context.user_data['pending_amount'] = amount
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Orqaga", callback_data="premium_info")],
    ])
    
    text = (
        f"💳 *To'lov ma'lumotlari*\n\n"
        f"📦 Tarif: *{plan_names.get(plan, plan)}*\n"
        f"💰 Summa: *${amount}*\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🏦 *Karta raqami:*\n"
        f"`{payment.get('card', 'Noma\\'lum')}`\n\n"
        f"👤 *Karta egasi:*\n"
        f"{payment.get('name', '')}\n\n"
        f"📝 *Izoh:* {payment.get('note', '')}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"✅ To'lovni amalga oshirgandan so'ng\n"
        f"*to'lov screenshotini* shu yerga yuboring.\n\n"
        f"⏱ Admin {payment.get('confirm_time', '1-2 soat')} ichida tasdiqlaydi."
    )
    
    await update.callback_query.edit_message_text(
        text, parse_mode="Markdown", reply_markup=keyboard
    )

async def handle_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """To'lov screenshotini qabul qilish"""
    user_id = update.effective_user.id
    user = await get_user(user_id)
    
    if not user:
        await update.message.reply_text("❌ Avval /start bosing!")
        return
    
    plan = context.user_data.get('pending_plan')
    amount = context.user_data.get('pending_amount', 0)
    
    if not plan:
        # Foydalanuvchi tasodifiy rasm yuborgan bo'lishi mumkin
        return
    
    photo = update.message.photo[-1]
    file_id = photo.file_id
    
    # Bazaga saqlash
    payment_id = await save_payment_request(user_id, plan, amount, file_id)
    
    # Adminga xabar
    plan_names = {"weekly": "1 Haftalik", "monthly": "1 Oylik", "quarterly": "3 Oylik"}
    
    admin_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{payment_id}_{user_id}_{plan}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{payment_id}_{user_id}"),
        ]
    ])
    
    admin_text = (
        f"💳 *Yangi to'lov so'rovi!*\n\n"
        f"👤 Foydalanuvchi: {user['full_name']}\n"
        f"📱 Tel: {user['phone']}\n"
        f"🆔 ID: `{user_id}`\n"
        f"📦 Tarif: {plan_names.get(plan, plan)}\n"
        f"💰 Summa: ${amount}\n"
        f"🔢 To'lov ID: #{payment_id}"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            await update.get_bot().send_photo(
                chat_id=admin_id,
                photo=file_id,
                caption=admin_text,
                parse_mode="Markdown",
                reply_markup=admin_keyboard
            )
        except Exception:
            pass
    
    # Foydalanuvchiga tasdiqlash xabari
    context.user_data.pop('pending_plan', None)
    context.user_data.pop('pending_amount', None)
    
    await update.message.reply_text(
        f"✅ *To'lov screenshoti qabul qilindi!*\n\n"
        f"📋 So'rov ID: #{payment_id}\n\n"
        f"⏱ Admin tez orada tekshiradi va Premium faollashtiriladi.\n"
        f"Saboingiz uchun rahmat! 🙏",
        parse_mode="Markdown"
    )
