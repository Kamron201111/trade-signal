"""
📈 TradeSignal Pro Bot
"""
import asyncio
import logging
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, CallbackQueryHandler, ConversationHandler
)
from config import BOT_TOKEN
from utils.database import init_db
from handlers.start import start_handler, collect_name, collect_phone
from handlers.market import handle_analyze_start, process_balance, handle_screenshot
from handlers.premium import premium_handler, handle_payment_screenshot
from handlers.admin import (
    admin_panel, handle_admin_callbacks,
    set_payment_command, set_price_command, give_premium_command
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

NAME, PHONE, BALANCE, SCREENSHOT = 0, 1, 2, 3

async def main():
    await init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # Ro'yxatdan o'tish
    reg_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start_handler)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_name)],
            PHONE: [MessageHandler((filters.TEXT | filters.CONTACT) & ~filters.COMMAND, collect_phone)],
        },
        fallbacks=[CommandHandler("start", start_handler)],
        allow_reentry=True
    )

    # Tahlil
    analysis_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_analyze_start, pattern="^analyze$")],
        states={
            BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_balance)],
            SCREENSHOT: [MessageHandler(filters.PHOTO, handle_screenshot)],
        },
        fallbacks=[CommandHandler("start", start_handler)],
    )

    app.add_handler(reg_conv)
    app.add_handler(analysis_conv)
    app.add_handler(CallbackQueryHandler(premium_handler, pattern="^premium"))
    app.add_handler(CallbackQueryHandler(premium_handler, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(handle_admin_callbacks, pattern="^admin"))
    app.add_handler(CallbackQueryHandler(handle_admin_callbacks, pattern="^(approve|reject)_"))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_payment_screenshot))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("setpayment", set_payment_command))
    app.add_handler(CommandHandler("setprice", set_price_command))
    app.add_handler(CommandHandler("givepremium", give_premium_command))

    logging.info("🚀 TradeSignal Pro Bot ishga tushdi!")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
