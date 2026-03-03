"""
📈 TradeSignal Pro Bot - Main Entry Point
"""
import asyncio
import logging
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, CallbackQueryHandler, ConversationHandler
)
from config import BOT_TOKEN
from utils.database import init_db

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
NAME, PHONE, BALANCE, SCREENSHOT = range(4)

async def main():
    await init_db()
    
    app = Application.builder().token(BOT_TOKEN).build()

    # Registration conversation
    from telegram.ext import ConversationHandler
    reg_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start_handler)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_name)],
            PHONE: [MessageHandler(filters.TEXT | filters.CONTACT, collect_phone)],
        },
        fallbacks=[CommandHandler("start", start_handler)],
    )

    # Analysis conversation
    analysis_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_balance, pattern="^analyze$")],
        states={
            BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_balance)],
            SCREENSHOT: [MessageHandler(filters.PHOTO, handle_screenshot)],
        },
        fallbacks=[CommandHandler("start", start_handler)],
    )

    app.add_handler(reg_conv)
    app.add_handler(analysis_conv)
    app.add_handler(CallbackQueryHandler(premium_handler, pattern="^premium"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_payment_screenshot))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(lambda u, c: None))

    logger.info("🚀 Bot ishga tushdi!")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
