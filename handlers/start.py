"""
👋 Start va ro'yxatdan o'tish handleri
"""
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from utils.database import get_user, register_user

NAME, PHONE = 0, 1

STICKERS = {
    "welcome": "CAACAgIAAxkBAAIBAmZ...",  # Telegram stiker ID (o'zgartirasiz)
}

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = await get_user(user.id)
    
    if db_user:
        await show_main_menu(update, context, db_user['full_name'])
        return ConversationHandler.END
    
    # Yangi foydalanuvchi - ro'yxatdan o'tkazish
    await update.message.reply_animation(
        animation="https://media.giphy.com/media/trading/giphy.gif",
        caption=(
            f"🌟 *Assalomu alaykum!*\n\n"
            f"📈 *TradeSignal Pro*ga xush kelibsiz!\n\n"
            f"Bu bot sizga professional darajada bozorni tahlil qilib, "
            f"aniq BUY/SELL signallari beradi.\n\n"
            f"Davom etish uchun ro'yxatdan o'ting 👇\n\n"
            f"📝 Ism va familiyangizni yozing:"
        ),
        parse_mode="Markdown"
    )
    return NAME

async def collect_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    
    if len(name) < 3 or len(name) > 50:
        await update.message.reply_text("❌ Iltimos, to'g'ri ism familiya kiriting (3-50 belgi)")
        return NAME
    
    context.user_data['full_name'] = name
    
    keyboard = [[KeyboardButton("📱 Raqamni ulashish", request_contact=True)]]
    await update.message.reply_text(
        f"✅ Ajoyib, *{name}*!\n\n"
        f"📱 Endi telefon raqamingizni yuboring:\n"
        f"_(tugmani bosing yoki qo'lda kiriting)_",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return PHONE

async def collect_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()
        # Raqam validatsiya
        clean = phone.replace("+", "").replace(" ", "").replace("-", "")
        if not clean.isdigit() or len(clean) < 9:
            await update.message.reply_text("❌ Noto'g'ri telefon raqam. Qayta kiriting:")
            return PHONE
    
    user = update.effective_user
    full_name = context.user_data.get('full_name', user.full_name)
    
    await register_user(user.id, user.username or "", full_name, phone)
    
    from telegram import ReplyKeyboardRemove
    await update.message.reply_text(
        f"🎉 *Tabriklaymiz, {full_name}!*\n\n"
        f"✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!\n\n"
        f"📊 Endi siz kuniga *3 ta bepul* signal olishingiz mumkin.\n"
        f"🚀 Cheksiz signallar uchun Premium obuna boring.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await show_main_menu(update, context, full_name)
    return ConversationHandler.END

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, name: str = ""):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Bozorni tahlil qilish", callback_data="analyze")],
        [InlineKeyboardButton("💎 Premium olish", callback_data="premium_info")],
        [InlineKeyboardButton("📋 Mening ma'lumotlarim", callback_data="my_info")],
        [InlineKeyboardButton("❓ Yordam", callback_data="help")],
    ])
    
    text = (
        f"🏠 *Asosiy menyu*\n\n"
        f"Salom, *{name or 'foydalanuvchi'}*! 👋\n\n"
        f"Nima qilmoqchisiz?"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
