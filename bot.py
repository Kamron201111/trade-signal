import logging
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, CallbackQueryHandler, ConversationHandler
)
from config import BOT_TOKEN
from utils.database import init_db
from handlers.start import cmd_start, get_name, get_phone, show_main_menu, show_profile, NAME, PHONE
from handlers.market import start_analyze, get_balance, get_screenshot, strategy_menu, set_strategy, BALANCE, SCREENSHOT
from handlers.premium import premium_info, buy_plan, handle_payment_photo
from handlers.admin import (
    cmd_admin, show_admin_menu, adm_callback, handle_broadcast,
    cmd_setprice, cmd_setcard, cmd_giveprem, cmd_ban
)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # Ro'yxatdan o'tish
    reg = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler((filters.TEXT | filters.CONTACT) & ~filters.COMMAND, get_phone)],
        },
        fallbacks=[CommandHandler("start", cmd_start)],
        allow_reentry=True,
        name="registration",
        persistent=False,
    )

    # Tahlil
    analysis = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_analyze, pattern="^analyze$")],
        states={
            BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_balance)],
            SCREENSHOT: [MessageHandler(filters.PHOTO, get_screenshot)],
        },
        fallbacks=[CommandHandler("start", cmd_start)],
        name="analysis",
        persistent=False,
    )

    app.add_handler(reg)
    app.add_handler(analysis)

    # Callback handlers
    app.add_handler(CallbackQueryHandler(show_main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(show_profile, pattern="^my_profile$"))
    app.add_handler(CallbackQueryHandler(premium_info, pattern="^premium_info$"))
    app.add_handler(CallbackQueryHandler(buy_plan, pattern="^buy_(weekly|monthly|quarterly)$"))
    app.add_handler(CallbackQueryHandler(strategy_menu, pattern="^strategy_menu$"))
    app.add_handler(CallbackQueryHandler(set_strategy, pattern="^setstrat_"))
    app.add_handler(CallbackQueryHandler(adm_callback, pattern="^adm_"))
    app.add_handler(CallbackQueryHandler(adm_callback, pattern="^(appr|rejt)_"))

    # Rasm handler (to'lov screenshoti)
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_payment_photo))

    # Broadcast
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_broadcast
    ))

    # Admin commands
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("setprice", cmd_setprice))
    app.add_handler(CommandHandler("setcard", cmd_setcard))
    app.add_handler(CommandHandler("giveprem", cmd_giveprem))
    app.add_handler(CommandHandler("ban", cmd_ban))

    logging.info("🚀 TradeSignal Pro ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
