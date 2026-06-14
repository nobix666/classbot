import os
import logging
from dotenv import load_dotenv

load_dotenv()

from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from database.db import connect_db
from handlers.academic import add_class, get_timetable_cmd, change_timetable_day, del_class, clear_day, class_reminder_job
from handlers.tasks import add_task, get_tasks
from handlers.menu import start, menu_handler
from handlers.admin_tools import import_members, mention_all
from handlers.funds import add_fund, clear_fund, check_fund
from handlers.custom_cmds import add_custom_cmd, del_custom_cmd, handle_custom_cmd
from handlers.tools import (
    show_creator, show_status, show_wifi, paginate_wifi,
    add_wifi, del_wifi, add_egg, del_egg,
    encrypt_decrypt, bin_to_hex, hex_to_bin
)

# 📌 ဤနေရာတွင် ရှုပ်နေသော social imports များကို တစ်ခုတည်း အဖြစ် သပ်သပ်ရပ်ရပ် ပေါင်းထားပါသည်
from handlers.social import (
    confess_start, confess_receive, confess_action,
    c1_start, c1_receive_msg, c1_receive_name, c1_action,
    notice_start, notice_receive, notice_action, cancel_conv,
    set_cooldown_cmd, set_cooldown_action, set_user_cooldown_cmd, set_daily_limit_cmd,
    admin_approval_action, approvers_cmd, approvers_callback, add_approver_receive, nickname_start, nickname_receive, nickname_action,
    CONFESS_MSG, CONFESS_CONFIRM, C1_MSG, C1_NAME, C1_CONFIRM,
    NOTICE_MSG, NOTICE_CONFIRM, APPROVER_ADD, NICK_MSG, NICK_CONFIRM
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")

async def on_startup(application):
    logger.info("Starting up Bot and connecting to Database...")
    await connect_db()

def main():
    if not TOKEN:
        logger.error("❌ TELEGRAM_TOKEN is missing!")
        return

    app = ApplicationBuilder().token(TOKEN).post_init(on_startup).build()

    # 🚀 Background Jobs
    app.job_queue.run_repeating(class_reminder_job, interval=60, first=10)

    # ================= CONVERSATION HANDLERS =================
    c1_conv = ConversationHandler(
        entry_points=[CommandHandler('confess', c1_start)],
        states={
            C1_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, c1_receive_msg)],
            C1_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, c1_receive_name)],
            C1_CONFIRM: [CallbackQueryHandler(c1_action, pattern="^(send|cancel)_c1")]
        },
        fallbacks=[CommandHandler('cancel', cancel_conv)]
    )
    app.add_handler(c1_conv)

    confess_conv = ConversationHandler(
        entry_points=[CommandHandler('confess1', confess_start)],
        states={
            CONFESS_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, confess_receive)],
            CONFESS_CONFIRM: [CallbackQueryHandler(confess_action, pattern="^(send|cancel)_confess")]
        },
        fallbacks=[CommandHandler('cancel', cancel_conv)]
    )
    app.add_handler(confess_conv)

    notice_conv = ConversationHandler(
        entry_points=[CommandHandler('notice', notice_start)],
        states={
            NOTICE_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, notice_receive)],
            NOTICE_CONFIRM: [CallbackQueryHandler(notice_action, pattern="^(send|cancel)_notice")]
        },
        fallbacks=[CommandHandler('cancel', cancel_conv)]
    )
    app.add_handler(notice_conv)

    # Main Menu & Start Command
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(menu_handler, pattern="^(menu_|back_to_main)"))

    # Fund Management Commands
    app.add_handler(CommandHandler("addfund", add_fund))
    app.add_handler(CommandHandler("clearfund", clear_fund))
    app.add_handler(CommandHandler("fund", check_fund))

    # Cooldown & Limits Management
    app.add_handler(CommandHandler("setcooldown", set_cooldown_cmd))
    app.add_handler(CallbackQueryHandler(set_cooldown_action, pattern="^setcd_"))
    app.add_handler(CommandHandler("setusercd", set_user_cooldown_cmd))
    app.add_handler(CommandHandler("setlimit", set_daily_limit_cmd))
    app.add_handler(CallbackQueryHandler(admin_approval_action, pattern="^(aprv_|rjct_)"))

    # General Tools & Information
    app.add_handler(CommandHandler('creator', show_creator))
    app.add_handler(CommandHandler('status', show_status))
    app.add_handler(CommandHandler('wifi', show_wifi))
    app.add_handler(CallbackQueryHandler(paginate_wifi, pattern="^wifi_page_"))
    
    # Admin System Commands
    app.add_handler(CommandHandler('addwifi', add_wifi))
    app.add_handler(CommandHandler('delwifi', del_wifi))
    app.add_handler(CommandHandler('addegg', add_egg))
    app.add_handler(CommandHandler('delegg', del_egg))

    # Crypto & Data Tools
    app.add_handler(CommandHandler(['encrypt', 'decrypt'], encrypt_decrypt))
    app.add_handler(CommandHandler('bin2hex', bin_to_hex))
    app.add_handler(CommandHandler('hex2bin', hex_to_bin))

    # Custom Commands Management
    app.add_handler(CommandHandler(['addcmd1', 'addcmd2', 'addcmd3'], add_custom_cmd))
    app.add_handler(CommandHandler('delcmd', del_custom_cmd))

    # Catch-all for Custom Commands
    app.add_handler(MessageHandler(filters.COMMAND, handle_custom_cmd), group=2)

    # 📌 Admin Approvers Management
    app.add_handler(CommandHandler("approvers", approvers_cmd))
    
    approver_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(approvers_callback, pattern="^(addapp_|delapp_|cancel_app)")],
        states={
            APPROVER_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_approver_receive)]
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)]
    )
    app.add_handler(approver_conv)

    # ================= STANDARD COMMANDS =================
    app.add_handler(CommandHandler("import", import_members))
    app.add_handler(CommandHandler("mention", mention_all))
    app.add_handler(CommandHandler("addclass", add_class))
    app.add_handler(CommandHandler("delclass", del_class))
    app.add_handler(CommandHandler("clearday", clear_day))
    
    # Task Management
    app.add_handler(CommandHandler("addtask", add_task))
    app.add_handler(CommandHandler(["tutorials", "tasks"], get_tasks))

    # 📌 Nickname Setup Conversation
    nickname_conv = ConversationHandler(
        entry_points=[CommandHandler('nickname', nickname_start)],
        states={
            NICK_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, nickname_receive)],
            NICK_CONFIRM: [CallbackQueryHandler(nickname_action, pattern="^savenick_")]
        },
        fallbacks=[CommandHandler('cancel', cancel_conv)]
    )
    app.add_handler(nickname_conv)

    # Timetable Handlers
    MAJORS = ["it", "mc", "archi", "ep", "ec", "me", "civil"]
    for major in MAJORS:
        app.add_handler(CommandHandler(major, get_timetable_cmd))

    app.add_handler(CallbackQueryHandler(change_timetable_day, pattern="^tt_"))

    logger.info("🟢 CLASS BOT SYSTEM ONLINE...")
    app.run_polling()

if __name__ == '__main__':
    main()