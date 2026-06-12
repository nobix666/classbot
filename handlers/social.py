import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

LOG_GROUP_ID = int(os.getenv("LOG_GROUP_ID", "0"))
FOOTER = "\n\n<pre>System by Ben | Omni-Net 🟢</pre>"

CONFESS_MSG, CONFESS_CONFIRM = range(2)
NOTICE_MSG, NOTICE_CONFIRM = range(2, 4)
C1_MSG, C1_NAME, C1_CONFIRM = range(4, 7)

# ================= MULTI-GROUP HELPER =================
def get_class_groups():
    """.env မှ CLASS_GROUP_ID များကို ကော်မာဖြင့်ခွဲ၍ List အဖြစ် ထုတ်ပေးမည်"""
    group_id_str = os.getenv("CLASS_GROUP_ID", "0")
    try:
        return [int(g.strip()) for g in group_id_str.split(",") if g.strip() and g.strip() != "0"]
    except ValueError:
        logger.error("CLASS_GROUP_ID format မှားယွင်းနေပါသည်။ ကော်မာဖြင့်သာ ခြားပါ။")
        return []

async def build_target_keyboard(context: ContextTypes.DEFAULT_TYPE, prefix_send: str, prefix_cancel: str):
    """Group များကိုရှာဖွေပြီး Send လုပ်မည့် Inline Keyboard တည်ဆောက်ပေးသော Helper"""
    group_ids = get_class_groups()
    keyboard = []
    
    for gid in group_ids:
        try:
            chat = await context.bot.get_chat(gid)
            title = chat.title[:25] + "..." if len(chat.title) > 25 else chat.title
        except:
            title = f"Group ID: {gid}"
            
        keyboard.append([InlineKeyboardButton(f"📤 SEND TO: {title}", callback_data=f"{prefix_send}_{gid}")])
        
    if len(group_ids) > 1:
        keyboard.append([InlineKeyboardButton("🌍 SEND TO: BOTH GROUPS", callback_data=f"{prefix_send}_all")])
        
    keyboard.append([InlineKeyboardButton("❌ ABORT", callback_data=prefix_cancel)])
    return InlineKeyboardMarkup(keyboard)

# ================= HELPER FUNCTIONS =================
async def auto_delete_job(context: ContextTypes.DEFAULT_TYPE):
    try: await context.bot.delete_message(chat_id=context.job.chat_id, message_id=context.job.data)
    except: pass

def schedule_delete(context, chat_id, msg_id, delay):
    context.job_queue.run_once(auto_delete_job, delay, chat_id=chat_id, data=msg_id)

async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("<pre>🚫 Canceled.</pre>", parse_mode=ParseMode.HTML)
    return ConversationHandler.END

# ================= ANONYMOUS CONFESSION (/confess1) =================
async def confess_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        try: await update.message.delete()
        except: pass
        warn = await update.message.reply_text("⚠️ DM Access Only.")
        schedule_delete(context, update.effective_chat.id, warn.message_id, 5)
        return ConversationHandler.END
    await update.message.reply_text("<b>🕵️ ANONYMOUS CONFESSION</b>\n<pre>Enter your message (Identity Hidden):</pre>", parse_mode=ParseMode.HTML)
    return CONFESS_MSG

async def confess_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['msg'] = update.message.text
    context.user_data['sender_id'] = update.effective_user.id
    context.user_data['sender_uname'] = update.effective_user.username or "No_Username"
    context.user_data['send_time'] = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    
    markup = await build_target_keyboard(context, "send_confess", "cancel_confess")
    await update.message.reply_text(
        f"<b>📝 VERIFY & SELECT TARGET</b>\n<pre>{update.message.text}</pre>",
        reply_markup=markup, parse_mode=ParseMode.HTML
    )
    return CONFESS_CONFIRM

async def confess_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("send_confess"):
        target = query.data.replace("send_confess_", "")
        group_ids = get_class_groups()
        target_ids = group_ids if target == "all" else [int(target)]
        
        msg = context.user_data.get('msg', '')
        
        for gid in target_ids:
            try: 
                await context.bot.send_message(chat_id=gid, text=f"<b>#Confession</b>\n<pre>{msg}</pre>\n\n<i>- Anonymous</i>{FOOTER}", parse_mode=ParseMode.HTML)
            except Exception as e: logger.error(f"Group {gid} သို့ပို့ရန်အဆင်မပြေပါ: {e}")
        
        if LOG_GROUP_ID != 0:
            log_txt = f"🚨 <b>SYSTEM LOG | #Confession (Anonymous)</b>\n🎯 <b>Target:</b> {target}\n👤 <b>User:</b> @{context.user_data['sender_uname']} (ID: <code>{context.user_data['sender_id']}</code>)\n🕒 <b>Time:</b> {context.user_data['send_time']}\n📝 <b>Content:</b>\n<pre>{msg}</pre>"
            try: await context.bot.send_message(LOG_GROUP_ID, text=log_txt, parse_mode=ParseMode.HTML)
            except: pass
        await query.edit_message_text("<pre>✅ DELIVERED.</pre>", parse_mode=ParseMode.HTML)
    else:
        await query.edit_message_text("<pre>🚫 ABORTED.</pre>", parse_mode=ParseMode.HTML)
    return ConversationHandler.END

# ================= CUSTOM CONFESSION (/confess) =================
async def c1_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        try: await update.message.delete()
        except: pass
        warn = await update.message.reply_text("⚠️ DM Access Only.")
        schedule_delete(context, update.effective_chat.id, warn.message_id, 5)
        return ConversationHandler.END
    await update.message.reply_text("<b>🎭 CONFESSION SYSTEM (NAME REQUIRED)</b>\n<pre>Enter your confession message:</pre>", parse_mode=ParseMode.HTML)
    return C1_MSG

async def c1_receive_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['c1_msg'] = update.message.text
    await update.message.reply_text("<b>✍️ SIGNATURE</b>\n<pre>Enter the name/signature you want to show (e.g. Ben):</pre>", parse_mode=ParseMode.HTML)
    return C1_NAME

async def c1_receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['c1_name'] = update.message.text
    context.user_data['sender_id'] = update.effective_user.id
    context.user_data['sender_uname'] = update.effective_user.username or "No_Username"
    context.user_data['send_time'] = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    
    msg = context.user_data['c1_msg']
    name = context.user_data['c1_name']
    
    markup = await build_target_keyboard(context, "send_c1", "cancel_c1")
    await update.message.reply_text(
        f"<b>📝 PREVIEW & SELECT TARGET</b>\n<pre>{msg}</pre>\n\n<i>- {name}</i>",
        reply_markup=markup, parse_mode=ParseMode.HTML
    )
    return C1_CONFIRM

async def c1_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("send_c1"):
        target = query.data.replace("send_c1_", "")
        group_ids = get_class_groups()
        target_ids = group_ids if target == "all" else [int(target)]
        
        msg = context.user_data.get('c1_msg', '')
        name = context.user_data.get('c1_name', 'Anonymous')
        
        for gid in target_ids:
            try: 
                await context.bot.send_message(chat_id=gid, text=f"<b>#Confession</b>\n<pre>{msg}</pre>\n\n<i>- {name}</i>{FOOTER}", parse_mode=ParseMode.HTML)
            except Exception as e: logger.error(f"Group {gid} သို့ပို့ရန်အဆင်မပြေပါ: {e}")
        
        if LOG_GROUP_ID != 0:
            log_txt = f"🚨 <b>SYSTEM LOG | #Confession (Custom)</b>\n🎯 <b>Target:</b> {target}\n👤 <b>User:</b> @{context.user_data['sender_uname']} (ID: <code>{context.user_data['sender_id']}</code>)\n🎭 <b>Signature:</b> {name}\n🕒 <b>Time:</b> {context.user_data['send_time']}\n📝 <b>Content:</b>\n<pre>{msg}</pre>"
            try: await context.bot.send_message(LOG_GROUP_ID, text=log_txt, parse_mode=ParseMode.HTML)
            except: pass
        await query.edit_message_text(f"<pre>✅ DELIVERED as '- {name}'.</pre>", parse_mode=ParseMode.HTML)
    else:
        await query.edit_message_text("<pre>🚫 ABORTED.</pre>", parse_mode=ParseMode.HTML)
    return ConversationHandler.END

# ================= NOTICE SYSTEM (/notice) =================
async def notice_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        try: await update.message.delete()
        except: pass
        warn = await update.message.reply_text("<pre>⚠️ DM Access Only.</pre>", parse_mode=ParseMode.HTML)
        schedule_delete(context, update.effective_chat.id, warn.message_id, 5)
        return ConversationHandler.END
    await update.message.reply_text("<b>📢 SECURE NOTICE SYSTEM</b>\n<pre>Enter your notice message:</pre>", parse_mode=ParseMode.HTML)
    return NOTICE_MSG

async def notice_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['notice_msg'] = update.message.text
    context.user_data['sender_id'] = update.effective_user.id
    context.user_data['sender_uname'] = update.effective_user.username or "No_Username"
    context.user_data['send_time'] = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

    markup = await build_target_keyboard(context, "send_notice", "cancel_notice")
    await update.message.reply_text(
        f"<b>📝 VERIFY & SELECT TARGET</b>\n<pre>{update.message.text}</pre>",
        reply_markup=markup, parse_mode=ParseMode.HTML
    )
    return NOTICE_CONFIRM

async def notice_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("send_notice"):
        target = query.data.replace("send_notice_", "")
        group_ids = get_class_groups()
        target_ids = group_ids if target == "all" else [int(target)]
        
        msg = context.user_data.get('notice_msg', '')
        
        for gid in target_ids:
            try: 
                await context.bot.send_message(chat_id=gid, text=f"<b>#Notice</b>\n<pre>{msg}</pre>\n\n<i>- Anonymous</i>{FOOTER}", parse_mode=ParseMode.HTML)
            except Exception as e: logger.error(f"Group {gid} သို့ပို့ရန်အဆင်မပြေပါ: {e}")
        
        if LOG_GROUP_ID != 0:
            log_txt = f"🚨 <b>SYSTEM LOG | #Notice</b>\n🎯 <b>Target:</b> {target}\n👤 <b>User:</b> @{context.user_data['sender_uname']} (ID: <code>{context.user_data['sender_id']}</code>)\n🕒 <b>Time:</b> {context.user_data['send_time']}\n📝 <b>Content:</b>\n<pre>{msg}</pre>"
            try: await context.bot.send_message(LOG_GROUP_ID, text=log_txt, parse_mode=ParseMode.HTML)
            except: pass
        await query.edit_message_text("<pre>✅ NOTICE DELIVERED.</pre>", parse_mode=ParseMode.HTML)
    else:
        await query.edit_message_text("<pre>🚫 ABORTED.</pre>", parse_mode=ParseMode.HTML)
    return ConversationHandler.END