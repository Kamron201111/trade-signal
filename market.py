"""
📊 Bozor tahlili handleri
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from utils.database import get_user, get_daily_usage, increment_usage, is_premium, save_analysis
from utils.analyzer import analyze_chart, detect_pair_from_image, format_signal_message, PAIR_LIST_TEXT
from config import FREE_DAILY_LIMIT
import io

BALANCE, SCREENSHOT = 2, 3

async def handle_analyze_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tahlil boshlash"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user = await get_user(user_id)
    
    if not user:
        await query.edit_message_text("❌ Avval /start bosing!")
        return ConversationHandler.END
    
    # Limit tekshirish
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
                "⛔ *Kunlik limit tugadi!*\n\n"
                f"Siz bugun {FREE_DAILY_LIMIT} ta bepul tahlildan foydalandingiz.\n\n"
                "🚀 *Cheksiz tahlil uchun Premium oling:*\n"
                "• Kunlik cheksiz signal\n"
                "• Barcha juftliklar\n"
                "• Priority tahlil\n\n"
                "💰 Narxlar juda qulay!",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            return ConversationHandler.END
        
        await query.edit_message_text(
            f"💼 *Balans miqdorini kiriting*\n\n"
            f"📊 Bugun qolgan signallar: *{remaining}/{FREE_DAILY_LIMIT}*\n\n"
            f"Savdo balansingiz qancha? (USD)\n"
            f"_Minimum: $5_\n\n"
            f"Raqamni yozing, masalan: `50` yoki `1000`",
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            "💼 *Balans miqdorini kiriting*\n\n"
            "💎 Premium foydalanuvchi — cheksiz signal!\n\n"
            "Savdo balansingiz qancha? (USD)\n"
            "_Minimum: $5_\n\n"
            "Raqamni yozing, masalan: `50` yoki `1000`",
            parse_mode="Markdown"
        )
    
    return BALANCE

# Alias
handle_balance = handle_analyze_start

async def process_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Balansni qabul qilish"""
    try:
        balance = float(update.message.text.strip().replace(",", ".").replace("$", ""))
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri miqdor. Faqat raqam kiriting, masalan: `100`", parse_mode="Markdown")
        return BALANCE
    
    if balance < 5:
        await update.message.reply_text(
            "❌ Minimum balans $5.\n"
            "Iltimos, kamida $5 kiriting:"
        )
        return BALANCE
    
    context.user_data['balance'] = balance
    
    await update.message.reply_text(
        f"✅ Balans: *${balance:.2f}*\n\n"
        f"📸 Endi *chart screenshotini* yuboring!\n\n"
        f"📋 Bot quyidagi juftliklarni tahlil qila oladi:\n\n"
        f"{PAIR_LIST_TEXT}",
        parse_mode="Markdown"
    )
    return SCREENSHOT

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Screenshot tahlil qilish"""
    user_id = update.effective_user.id
    
    # Fotodan ma'lumot olish
    photo = update.message.photo[-1]  # Eng yuqori sifat
    
    processing_msg = await update.message.reply_text(
        "⏳ *Tahlil qilinmoqda...*\n\n"
        "🔍 Chart o'rganilmoqda...\n"
        "📊 Strategiyalar qo'llanilmoqda...\n"
        "🧮 Risk hisoblanmoqda...",
        parse_mode="Markdown"
    )
    
    try:
        # Rasmni yuklab olish
        file = await photo.get_file()
        img_bytes = await file.download_as_bytearray()
        
        balance = context.user_data.get('balance', 100)
        
        # Juftlikni aniqlash
        await processing_msg.edit_text(
            "🔍 *Juftlik aniqlanmoqda...*",
            parse_mode="Markdown"
        )
        pair = await detect_pair_from_image(bytes(img_bytes))
        
        await processing_msg.edit_text(
            f"✅ Juftlik: *{pair}*\n"
            f"📊 *Tahlil qilinmoqda...*",
            parse_mode="Markdown"
        )
        
        # Tahlil
        result = await analyze_chart(bytes(img_bytes), balance, pair)
        
        # Bazaga saqlash
        await save_analysis(user_id, result)
        await increment_usage(user_id)
        
        # Signalni yuborish
        await processing_msg.delete()
        
        signal_text = format_signal_message(result)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Yana tahlil qilish", callback_data="analyze")],
            [InlineKeyboardButton("🏠 Asosiy menyu", callback_data="main_menu")],
        ])
        
        await update.message.reply_text(
            signal_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        await processing_msg.edit_text(
            "❌ *Xatolik yuz berdi!*\n\n"
            "Iltimos, aniq chart screenshotini yuboring.\n"
            "_(Grafik ko'rinib turishi kerak)_",
            parse_mode="Markdown"
        )
    
    return ConversationHandler.END
