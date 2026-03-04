from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import ContextTypes, ConversationHandler
from utils.database import db_get_user, db_register_user, db_is_premium, db_get_usage
from config import FREE_DAILY_LIMIT

NAME, PHONE, BALANCE, SCREENSHOT, WAITING_PAYMENT = 0, 1, 2, 3, 4

def main_keyboard():
    return ReplyKeyboardMarkup([
        ["📊 Tahlil qilish", "📐 Strategiya"],
        ["💎 Premium", "👤 Profil"],
    ], resize_keyboard=True, is_persistent=True)

async def cmd_start(update, context):
    user = update.effective_user
    db_user = db_get_user(user.id)
    if db_user:
        await update.message.reply_text(
            "Xush kelibsiz!",
            reply_markup=main_keyboard()
        )
        await show_inline_menu(update, context)
        return ConversationHandler.END
    await update.message.reply_text(
        "Assalomu alaykum!\n\n"
        "📈 TradeSignal Pro ga xush kelibsiz!\n\n"
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
    kb = [[KeyboardButton("📱 Raqamni ulashish", request_contact=True)]]
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
        "Tabriklaymiz! Ro'yxatdan o'tdingiz!\n\n"
        "Kuniga " + str(FREE_DAILY_LIMIT) + " ta bepul tahlil olasiz.",
        reply_markup=main_keyboard()
    )
    await show_inline_menu(update, context)
    return ConversationHandler.END

async def show_inline_menu(update, context):
    user_id = update.effective_user.id
    prem = db_is_premium(user_id)
    usage = db_get_usage(user_id)
    remaining = "Cheksiz" if prem else str(FREE_DAILY_LIMIT - usage)
    badge = " 💎" if prem else ""
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Bozorni tahlil qilish", callback_data="analyze")],
        [InlineKeyboardButton("📐 Strategiyani tanlash", callback_data="strategy_menu")],
        [InlineKeyboardButton("💎 Premium obuna", callback_data="premium_info")],
        [InlineKeyboardButton("👤 Profil", callback_data="my_profile")],
    ])
    text = (
        "Bosh menyu" + badge + "\n\n"
        "Bugungi tahlillar: " + (str(usage) if not prem else "Cheksiz") + "\n"
        "Qolgan: " + remaining
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb)
    else:
        await update.message.reply_text(text, reply_markup=kb)

async def show_main_menu(update, context):
    if update.callback_query:
        await update.callback_query.answer()
    await show_inline_menu(update, context)

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
        prem_text += " (muddati: " + until.strftime("%d.%m.%Y") + ")"
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

async def handle_menu_buttons(update, context):
    text = update.message.text
    user = db_get_user(update.effective_user.id)
    if not user:
        await cmd_start(update, context)
        return
    if text == "📐 Strategiya":
        await show_strategy_text(update, context)
    elif text == "💎 Premium":
        await show_premium_text(update, context)
    elif text == "👤 Profil":
        await show_profile_text(update, context)
    else:
        await show_inline_menu(update, context)

async def show_strategy_text(update, context):
    from utils.database import db_get_strategy, db_is_premium
    from utils.analyzer import STRATEGIES, FREE_STRATEGIES, PREMIUM_STRATEGIES
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
    await update.message.reply_text(
        "Strategiyani tanlang:\n\nHozirgi: " + STRATEGIES.get(current, current),
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def show_premium_text(update, context):
    from utils.database import db_get_setting, db_is_premium
    prem = db_is_premium(update.effective_user.id)
    prices = db_get_setting("prices") or {"weekly": 50000, "monthly": 150000, "quarterly": 350000}
    status = "Sizda hozir Premium bor!\n\n" if prem else ""
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("1 Haftalik — " + str(prices["weekly"]) + " so'm", callback_data="buy_weekly")],
        [InlineKeyboardButton("1 Oylik — " + str(prices["monthly"]) + " so'm", callback_data="buy_monthly")],
        [InlineKeyboardButton("3 Oylik — " + str(prices["quarterly"]) + " so'm", callback_data="buy_quarterly")],
        [InlineKeyboardButton("Orqaga", callback_data="main_menu")],
    ])
    await update.message.reply_text(
        status + "💎 Premium Obuna\n\n"
        "✅ Cheksiz kunlik tahlil\n"
        "✅ 100 ta juftlik\n"
        "✅ Barcha 10 ta strategiya\n"
        "✅ Strategiyani o'zing tanlash\n\n"
        "Tarif tanlang:",
        reply_markup=kb
    )

async def show_profile_text(update, context):
    user_id = update.effective_user.id
    user = db_get_user(user_id)
    prem = db_is_premium(user_id)
    usage = db_get_usage(user_id)
    if not user:
        await update.message.reply_text("Avval /start bosing!")
        return
    prem_text = "💎 Premium" if prem else "Bepul"
    if prem and user.get("premium_until"):
        from datetime import datetime
        until = datetime.fromisoformat(user["premium_until"])
        prem_text += " (muddati: " + until.strftime("%d.%m.%Y") + ")"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Orqaga", callback_data="main_menu")]])
    await update.message.reply_text(
        "Mening profilim\n\n"
        "Ism: " + user["full_name"] + "\n"
        "Tel: " + user["phone"] + "\n"
        "ID: " + str(user_id) + "\n"
        "Obuna: " + prem_text + "\n"
        "Bugungi tahlillar: " + str(usage),
        reply_markup=kb
    )
