import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# ================= 🗑 Auto Delete စနစ် =================
async def auto_delete_job(context: ContextTypes.DEFAULT_TYPE):
    try: await context.bot.delete_message(chat_id=context.job.chat_id, message_id=context.job.data)
    except: pass

def schedule_delete(context, chat_id, msg_id, delay=300):
    """မူလသတ်မှတ်ချက် ၅ မိနစ် (စက္ကန့် ၃၀၀) ဖြင့် ဖျက်မည်"""
    context.job_queue.run_once(auto_delete_job, delay, chat_id=chat_id, data=msg_id)

async def is_admin_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    if user_id == OWNER_ID: return True
    if update.effective_chat.type in ['group', 'supergroup']:
        try:
            admins = await context.bot.get_chat_administrators(update.effective_chat.id)
            admin_ids = [admin.user.id for admin in admins]
            if user_id in admin_ids: return True
        except: pass
    return False

def get_main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎓 Academic", callback_data="menu_academic"),
            InlineKeyboardButton("💬 Social", callback_data="menu_social")
        ],
        [InlineKeyboardButton("🛠️ Utility Node", callback_data="menu_tools")],
        [InlineKeyboardButton("⚠️ Admin Console", callback_data="menu_admin")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start ခေါ်သည့်အခါ Animation ဖြင့် Boot တက်မည့်စနစ်"""
    chat_id = update.effective_chat.id
    user_msg_id = update.message.message_id
    
    msg = await update.message.reply_text("<pre>Initializing Omni-Net... [■■□□□]</pre>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(0.5)
    await msg.edit_text("<pre>Bypassing Security... [■■■■□]</pre>", parse_mode=ParseMode.HTML)
    await asyncio.sleep(0.5)
    
    main_text = """<blockquote><b>🟢 OMNI-NET TERMINAL V3.0</b></blockquote>
<pre>System Status: Online
Access Level : Granted</pre>

Select Operation Protocol:"""
    
    await msg.edit_text(text=main_text, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML)
    
    # 👈 Menu နှင့် User စာကို မိနစ် ၅ မိနစ်အကြာတွင် အလိုလိုဖျက်မည်
    schedule_delete(context, chat_id, user_msg_id, 300)
    schedule_delete(context, chat_id, msg.message_id, 300)

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.data == "back_to_main":
        await query.answer()
        main_text = """<blockquote><b>🟢 OMNI-NET TERMINAL V3.0</b></blockquote>
<pre>System Status: Online
Access Level : Granted</pre>

Select Operation Protocol:"""
        await query.edit_message_text(main_text, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML)
        return

    back_kb = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]]

    if query.data == "menu_academic":
        await query.answer()
        text = """<blockquote><b>🎓 ACADEMIC CORE</b></blockquote>
<pre>📌 အချိန်ဇယား ကြည့်ရန်:
/it, /ec, /civil, /ep, /me, /mc, /archi

📌 တာဝန်နှင့် စာမေးပွဲများ:
/tasks (သို့) /tutorials</pre>"""
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(back_kb), parse_mode=ParseMode.HTML)

    elif query.data == "menu_social":
        await query.answer()
        text = """<blockquote><b>💬 SOCIAL HUB</b></blockquote>
<pre>📌 ရင်ဖွင့် / စနောက်ရန် (DM မှသုံးပါ):
/confess (နာမည်တပ်၍ ပို့ရန်)
/confess1 (Anonymous ပို့ရန်)
/notice (ကြေညာချက်/စနောက်စာ ပို့ရန်)</pre>"""
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(back_kb), parse_mode=ParseMode.HTML)

    elif query.data == "menu_tools":
        await query.answer()
        text = """<blockquote><b>🛠️ UTILITY NODE</b></blockquote>
<pre>📌 အထွေထွေ Tool များ:
/wifi - အတန်းတွင်း WiFi ကြည့်ရန်
/status - ဆာဗာ အခြေအနေ ကြည့်ရန်
/creator - System Info ကြည့်ရန်

📌 လျှို့ဝှက်ကုဒ် Tool များ:
/encrypt &lt;စာသား&gt;
/decrypt &lt;ကုဒ်&gt;
/bin2hex &lt;Binary&gt;
/hex2bin &lt;Hex&gt;</pre>"""
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(back_kb), parse_mode=ParseMode.HTML)

    elif query.data == "menu_admin":
        if await is_admin_check(update, context):
            await query.answer()
            text = """<blockquote><b>⚠️ ADMIN CONSOLE</b></blockquote>
<pre>📌 စီမံခန့်ခွဲမှုများ:
/mention - အားလုံးကို Tag ခေါ်ရန်
/import - CSV မှ Member သွင်းရန်

📌 Bot ကို စာသင်ပေးရန်:
/addcmd1, /addcmd2, /addcmd3
/delcmd

📌 အခြား စနစ်များ:
/addwifi, /delwifi
/addclass, /delclass, /clearday
/addtask
/addegg, /delegg</pre>"""
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(back_kb), parse_mode=ParseMode.HTML)
        else:
            await query.answer("⛔ Access Denied: Level 9 Clearance Required.", show_alert=True)