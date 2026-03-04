from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from utils.database import db_get_user, db_get_usage, db_increment_usage, db_is_premium, db_save_analysis, db_get_strategy
from utils.analyzer import analyze, detect_pair, format_signal, PAIR_LIST_TEXT, FREE_STRATEGIES, PREMIUM_STRATEGIES, STRATEGIES
from config import FREE_DAILY_LIMIT

BALANCE, SCREENSHOT = 2, 3

def _check_limit(user_id):
    prem = db_is_premium(user_id)
    if prem:
        return True, 0
    usage = db_get_usage(user_id)
    remaining = FREE_DAILY_LIMIT - usage
    return remaining > 0, remaining

async def _limit_exceeded(target, context):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Premium olish", callback_data="premium_info")],
        [InlineKeyboardButton("Orqaga", callback_data="main_menu")],
    ])
    text = (
        "Kunlik limit tugadi!\n\n"
        "Bugun " + str(FREE_DAILY_LIMIT) + " ta bepul tahlildan foydalandingiz.\n\n"
        "Cheksiz tahlil uchun Premium oling!"
    )
    if hasattr(target, "edit_message_text"):
        await target.edit_message_text(text, reply_markup=kb)
    else:
        await target.reply_text(text, reply_markup=kb)

# Inline callback orqali
async def start_analyze(update, context):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if not db_get_user(user_id):
        await query.edit_message_text("Avval /start bosing!")
        return ConversationHandler.END
    ok, remaining = _check_limit(user_id)
    if not ok:
        await _limit_exceeded(query, context)
        return ConversationHandler.END
    prem = db_is_premium(user_id)
    rem_text = "Cheksiz tahlil!\n\n" if prem else "Bugun qolgan: " + str(remaining) + "/" + str(FREE_DAILY_LIMIT) + "\n\n"
    await query.edit_message_text(rem_text + "Savdo balansingiz qancha? (USD)\nMasalan: 100\nMinimum: $5")
    return BALANCE

# Pastki keyboard tugmasi orqali
async def start_analyze_text(update, context):
    user_id = update.effective_user.id
    if not db_get_user(user_id):
        await update.message.reply_text("Avval /start bosing!")
        return ConversationHandler.END
    ok, remaining = _check_limit(user_id)
    if not ok:
        await _limit_exceeded(update.message, context)
        return ConversationHandler.END
    prem = db_is_premium(user_id)
    rem_text = "Cheksiz tahlil!\n\n" if prem else "Bugun qolgan: " + str(remaining) + "/" + str(FREE_DAILY_LIMIT) + "\n\n"
    await update.message.reply_text(rem_text + "Savdo balansingiz qancha? (USD)\nMasalan: 100\nMinimum: $5")
    return BALANCE

async def get_balance(update, context):
    try:
        balance = float(update.message.text.strip().replace(",",".").replace("$","").replace(" ",""))
    except ValueError:
        await update.message.reply_text("Faqat raqam kiriting. Masalan: 100")
        return BALANCE
    if balance < 5:
        await update.message.reply_text("Minimum balans $5. Qayta kiriting:")
        return BALANCE
    context.user_data["balance"] = balance
    strategy_key = db_get_strategy(update.effective_user.id)
    strategy_name = STRATEGIES.get(strategy_key, "Avtomatik")
    await update.message.reply_text(
        "Balans: $" + str(balance) + "\n"
        "Strategiya: " + strategy_name + "\n\n"
        "Endi chart screenshotini yuboring!\n\n" + PAIR_LIST_TEXT
    )
    return SCREENSHOT

async def get_screenshot(update, context):
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    msg = await update.message.reply_text("Tahlil qilinmoqda...")
    try:
        file = await photo.get_file()
        img_bytes = bytes(await file.download_as_bytearray())
        balance = context.user_data.get("balance", 100)
        strategy_key = db_get_strategy(user_id)
        await msg.edit_text("Juftlik aniqlanmoqda...")
        pair = await detect_pair(img_bytes)
        await msg.edit_text("Juftlik: " + pair + "\nTaghlil qilinmoqda...")
        result = await analyze(img_bytes, balance, pair, strategy_key)
        db_save_analysis(user_id, pair, result.get("signal"), result.get("entry",0),
                        result.get("sl",0), result.get("tp",0), balance)
        db_increment_usage(user_id)
        await msg.delete()
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Yana tahlil", callback_data="analyze"),
             InlineKeyboardButton("Bosh menyu", callback_data="main_menu")],
        ])
        await update.message.reply_text(format_signal(result), reply_markup=kb)
    except Exception as e:
        print("Screenshot xato:", e)
        await msg.edit_text(
            "Tahlil qilishda xatolik!\n\n"
            "Iltimos aniq chart screenshotini yuboring.\n"
            "Juftlik nomi ko'rinib tursin."
        )
    return ConversationHandler.END

async def strategy_menu(update, context):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    prem = db_is_premium(user_id)
    current = db_get_strategy(user_id)
    available = PREMIUM_STRATEGIES if prem else FREE_STRATEGIES
    buttons = []
    for key in available:
        name = STRATEGIES[key]
        mark = "✅ " if key == current else ""
        buttons.append([InlineKeyboardButton(mark + name, callback_data="setstrat_" + key)])
    if not prem:
        buttons.append([InlineKeyboardButton("💎 Premium — barcha strategiyalar", callback_data="premium_info")])
    buttons.append([InlineKeyboardButton("Orqaga", callback_data="main_menu")])
    await query.edit_message_text(
        "Strategiyani tanlang:\n\nHozirgi: " + STRATEGIES.get(current, current),
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def set_strategy(update, context):
    query = update.callback_query
    user_id = update.effective_user.id
    prem = db_is_premium(user_id)
    key = query.data.replace("setstrat_", "")
    if not prem and key not in FREE_STRATEGIES:
        await query.answer("Bu strategiya faqat Premium uchun!", show_alert=True)
        return
    from utils.database import db_set_strategy
    db_set_strategy(user_id, key)
    await query.answer("Strategiya saqlandi!", show_alert=False)
    await strategy_menu(update, context)
