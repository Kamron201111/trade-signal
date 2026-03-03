from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from utils.database import get_user, get_daily_usage, increment_usage, is_premium, save_analysis
from utils.analyzer import analyze_chart, detect_pair_from_image, format_signal_message, PAIR_LIST_TEXT

FREE_DAILY_LIMIT = 3
BALANCE, SCREENSHOT = 2, 3

async def handle_analyze_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        await query.edit_message_text("Avval /start bosing!")
        return ConversationHandler.END
    premium = await is_premium(user_id)
    if not premium:
        usage = await get_daily_usage(user_id)
        remaining = FREE_DAILY_LIMIT - usage
        if remaining <= 0:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Premium olish", callback_data="premium_info")],
                [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="main_menu")],
            ])
            await query.edit_message_text(
                "Kunlik limit tugadi!\n\n"
                "Bugun " + str(FREE_DAILY_LIMIT) + " ta bepul tahlildan foydalandingiz.\n\n"
                "Cheksiz signal uchun Premium oling!",
                reply_markup=keyboard
            )
            return ConversationHandler.END
        await query.edit_message_text(
            "Balans miqdorini kiriting (USD)\n\n"
            "Bugun qolgan: " + str(remaining) + "/" + str(FREE_DAILY_LIMIT) + "\n\n"
            "Masalan: 50 yoki 1000\nMinimum: $5"
        )
    else:
        await query.edit_message_text(
            "Balans miqdorini kiriting (USD)\n\n"
            "Premium - cheksiz signal!\n\n"
            "Masalan: 50 yoki 1000\nMinimum: $5"
        )
    return BALANCE

async def process_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        balance = float(update.message.text.strip().replace(",", ".").replace("$", ""))
    except ValueError:
        await update.message.reply_text("Noto'g'ri miqdor. Faqat raqam kiriting, masalan: 100")
        return BALANCE
    if balance < 5:
        await update.message.reply_text("Minimum balans $5. Qayta kiriting:")
        return BALANCE
    context.user_data["balance"] = balance
    await update.message.reply_text(
        "Balans: $" + str(balance) + "\n\n"
        "Endi chart screenshotini yuboring!\n\n" + PAIR_LIST_TEXT
    )
    return SCREENSHOT

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    msg = await update.message.reply_text("Tahlil qilinmoqda...")
    try:
        file = await photo.get_file()
        img_bytes = await file.download_as_bytearray()
        balance = context.user_data.get("balance", 100)
        await msg.edit_text("Juftlik aniqlanmoqda...")
        pair = await detect_pair_from_image(bytes(img_bytes))
        await msg.edit_text("Juftlik: " + pair + "\nTaghlil qilinmoqda...")
        result = await analyze_chart(bytes(img_bytes), balance, pair)
        await save_analysis(user_id, result)
        await increment_usage(user_id)
        await msg.delete()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Yana tahlil", callback_data="analyze")],
            [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="main_menu")],
        ])
        await update.message.reply_text(
            format_signal_message(result),
            reply_markup=keyboard
        )
    except Exception as e:
        print("Tahlil xato:", e)
        await msg.edit_text("Xatolik! Aniq chart screenshotini yuboring.")
    return ConversationHandler.END
