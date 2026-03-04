from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from utils.database import db_get_user, db_register_user, db_is_premium, db_get_usage
from config import FREE_DAILY_LIMIT

NAME, PHONE, BALANCE, SCREENSHOT, WAITING_PAYMENT = 0, 1, 2, 3, 4

async def cmd_start(update, context):
    user = update.effective_user
    db_user = db_get_user(user.id)
    if db_user:
        await show_main_menu(update, context)
        return ConversationHandler.END
    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\n"
        "📈 TradeSignal Pro — professional trading signal boti\n\n"
        "Ro'yxatdan o'tish uchun ism va familiyangizni yozing:\n"
        "(Masalan: Alisher Karimov)"
    )
    return NAME

async def get_name(update, context):
    name = update.message.text.strip()
    if len(name) < 3:
        await update.message.reply_text("Iltimos, to'liq ism familiya kiriting:")
        return NAME
    context.user_data["full_name"] = name
    kb = [[KeyboardButton("📱 Raqamni avtomatik ulashish", request_contact=True)]]
    await update.message.reply_text(
        "Telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
    )
    return PHONE

async def get_phone(update, context):
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()
        clean = phone.replace("+","").replace(" ","").replace("-","")
        if not clean.isdigit() or len(clean) < 9:
            await update.message.reply_text("Noto'g'ri raqam. Qayta kiriting:")
            return PHONE
    user = update.effective_user
    full_name = context.user_data.get("full_name", user.full_name)
    db_register_user(user.id, user.username or "", full_name, phone)
    await update.message.reply_text(
        "Tabriklaymiz! ✅\n\n"
        "Ro'yxatdan muvaffaqiyatli o'tdingiz!\n\n"
        "Kuniga " + str(FREE_DAILY_LIMIT) + " ta bepul tahlil olasiz.",
        reply_markup=ReplyKeyboardRemove()
    )
    await show_main_menu(update, context)
    return ConversationHandler.END

async def show_main_menu(update, context):
    user_id = update.effective_user.id
    prem = db_is_premium(user_id)
    usage = db_get_usage(user_id)
    remaining = "Cheksiz" if prem else str(FREE_DAILY_LIMIT - usage)
    prem_badge = " 💎" if prem else ""

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Bozorni tahlil qilish", callback_data="analyze")],
        [InlineKeyboardButton("📐 Strategiyani tanlash", callback_data="strategy_menu")],
        [InlineKeyboardButton("💎 Premium obuna", callback_data="premium_info")],
        [InlineKeyboardButton("👤 Mening profilim", callback_data="my_profile")],
    ])

    text = (
        "Bosh menyu" + prem_badge + "\n\n"
        "Bugungi tahlillar: " + str(usage if not prem else "∞") + "\n"
        "Qolgan: " + remaining + "\n\n"
        "Nima qilmoqchisiz?"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb)
    else:
        await update.message.reply_text(text, reply_markup=kb)

async def show_profile(update, context):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user = db_get_user(user_id)
    prem = db_is_premium(user_id)
    usage = db_get_usage(user_id)
    if not user:
        await query.edit_message_text("Avval /start bosing!")
        return
    prem_text = "💎 Premium" if prem else "Bepul"
    if prem and user.get("premium_until"):
        from datetime import datetime
        until = datetime.fromisoformat(user["premium_until"])
        prem_text += "\nMuddati: " + until.strftime("%d.%m.%Y")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="main_menu")]])
    await query.edit_message_text(
        "Mening profilim\n\n"
        "Ism: " + user["full_name"] + "\n"
        "Tel: " + user["phone"] + "\n"
        "ID: " + str(user_id) + "\n"
        "Obuna: " + prem_text + "\n"
        "Bugungi tahlillar: " + str(usage),
        reply_markup=kb
    )
