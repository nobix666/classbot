import os
import uuid
import random
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from database.db import get_db

logger = logging.getLogger(__name__)

OWNER_ID = int(os.getenv("OWNER_ID", "0"))
LOG_GROUP_ID = int(os.getenv("LOG_GROUP_ID", "0"))
FOOTER = "\n\n<pre>System by Ben | Omni-Net 🟢</pre>"

# 📌 Random Emojis စာရင်း (Default Identity အတွက်)
RANDOM_EMOJIS = ["🦊", "🐼", "🐯", "🦁", "🐮", "🐷", "🐸", "🐵", "🐔", "🐧", "🦉", "🦄", "🐝", "🦋", "🐙", "🐢", "🐍", "🐳", "🐉", "🌵", "🌻", "🍎", "🍉", "🍓", "🍕", "🍔", "🍩", "⚽", "🎸", "🚗", "🚀", "💎", "🔮", "🎭", "🎨", "🤡", "👻", "👽", "👾", "🤖"]

CONFESS_MSG, CONFESS_CONFIRM = range(2)
NOTICE_MSG, NOTICE_CONFIRM = range(2, 4)
C1_MSG, C1_NAME, C1_CONFIRM = range(4, 7)
APPROVER_ADD = 7
NICK_MSG, NICK_CONFIRM = range(8, 10)

# ================= MULTI-GROUP & RESTRICTION HELPER =================
def get_class_groups():
    group_id_str = os.getenv("CLASS_GROUP_ID", "0")
    try:
        return [int(g.strip()) for g in group_id_str.split(",") if g.strip() and g.strip() != "0"]
    except ValueError:
        logger.error("CLASS_GROUP_ID format မှားယွင်းနေပါသည်။")
        return []

async def get_allowed_groups(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> list[int]:
    """တတိယမြောက် Group အတွက် Membership စစ်ဆေးပေးသည့် Function"""
    group_ids = get_class_groups()
    allowed = []
    for idx, gid in enumerate(group_ids):
        # 📌 idx == 2 ဆိုသည်မှာ ကော်မာဖြင့်ခြားထားသော တတိယမြောက် Group ကို ဆိုလိုသည်
        if idx == 2:
            try:
                member = await context.bot.get_chat_member(chat_id=gid, user_id=user_id)
                if member.status in ['member', 'administrator', 'creator', 'restricted']:
                    allowed.append(gid)
            except Exception as e:
                # Bot ကို Kick ထားလျှင် သို့မဟုတ် User မရှိလျှင် Error တက်မည်ဖြစ်၍ ကျော်သွားပါမည်
                pass 
        else:
            allowed.append(gid)
    return allowed

async def build_target_keyboard(user_id: int, context: ContextTypes.DEFAULT_TYPE, prefix_send: str, prefix_cancel: str):
    allowed_groups = await get_allowed_groups(user_id, context)
    keyboard = []
    
    for gid in allowed_groups:
        try:
            chat = await context.bot.get_chat(gid)
            title = chat.title[:25] + "..." if len(chat.title) > 25 else chat.title
        except:
            title = f"Group ID: {gid}"
        keyboard.append([InlineKeyboardButton(f"📤 SEND TO: {title}", callback_data=f"{prefix_send}_{gid}")])
        
    if len(allowed_groups) > 1:
        keyboard.append([InlineKeyboardButton("🌍 SEND TO: ALL ALLOWED GROUPS", callback_data=f"{prefix_send}_all")])
        
    keyboard.append([InlineKeyboardButton("❌ ABORT", callback_data=prefix_cancel)])
    return InlineKeyboardMarkup(keyboard)

# ================= IDENTITY HELPER (EMOJI / NICKNAME) =================
async def get_user_identity(user_id: int) -> str:
    db = get_db()
    if db is None: return f"#{str(user_id)[-4:]}"
    user_data = await db.user_settings.find_one({"user_id": user_id})
    if user_data:
        if "nickname" in user_data and user_data["nickname"]: return user_data["nickname"]
        if "emoji" in user_data and user_data["emoji"]: return user_data["emoji"]
    new_emoji = random.choice(RANDOM_EMOJIS)
    await db.user_settings.update_one({"user_id": user_id}, {"$set": {"emoji": new_emoji}}, upsert=True)
    return new_emoji

# ================= HELPER FUNCTIONS =================
async def auto_delete_job(context: ContextTypes.DEFAULT_TYPE):
    try: await context.bot.delete_message(chat_id=context.job.chat_id, message_id=context.job.data)
    except: pass

def schedule_delete(context, chat_id, msg_id, delay):
    context.job_queue.run_once(auto_delete_job, delay, chat_id=chat_id, data=msg_id)

async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("<pre>🚫 Canceled.</pre>", parse_mode=ParseMode.HTML)
    return ConversationHandler.END

# ================= ⏳ DAILY LIMIT & COOLDOWN SYSTEM =================
async def get_daily_limit() -> int:
    db = get_db()
    if db is None: return 3
    setting = await db.settings.find_one({"type": "daily_limit"})
    return setting.get("count", 3) if setting else 3

async def check_daily_limit(user_id: int) -> tuple[bool, int]:
    limit = await get_daily_limit()
    if limit == 0: return True, 0
    db = get_db()
    if db is None: return True, limit
    today_str = datetime.now().strftime("%Y-%m-%d")
    record = await db.daily_limits.find_one({"user_id": user_id, "date": today_str})
    if record and record.get("count", 0) >= limit: return False, limit
    return True, limit

async def increment_daily_limit(user_id: int):
    db = get_db()
    if db is None: return
    today_str = datetime.now().strftime("%Y-%m-%d")
    await db.daily_limits.update_one({"user_id": user_id, "date": today_str}, {"$inc": {"count": 1}}, upsert=True)

async def check_user_cooldown(user_id: int) -> int:
    db = get_db()
    if db is None: return 0
    user_setting = await db.user_settings.find_one({"user_id": user_id})
    if user_setting and "custom_cooldown" in user_setting: limit_mins = user_setting["custom_cooldown"]
    else:
        global_setting = await db.settings.find_one({"type": "cooldown_limit"})
        limit_mins = global_setting.get("minutes", 0) if global_setting else 0
    if limit_mins == 0: return 0
    user_data = await db.user_cooldowns.find_one({"user_id": user_id})
    if not user_data: return 0
    last_used = user_data.get("last_used")
    if not last_used: return 0
    now = datetime.now()
    passed_time = (now - last_used).total_seconds()
    required_time = limit_mins * 60
    if passed_time < required_time: return int(required_time - passed_time)
    return 0

async def update_user_cooldown(user_id: int):
    db = get_db()
    if db is None: return
    await db.user_cooldowns.update_one({"user_id": user_id}, {"$set": {"last_used": datetime.now()}}, upsert=True)

async def show_cooldown_warning(update: Update, remain_sec: int, context: ContextTypes.DEFAULT_TYPE):
    m, s = divmod(remain_sec, 60)
    h, m = divmod(m, 60)
    time_str = f"{int(h)} နာရီ {int(m)} မိနစ်" if h > 0 else f"{int(m)} မိနစ် {int(s)} စက္ကန့်"
    warn = await update.message.reply_text(f"⏳ <b>COOLDOWN ACTIVE</b>\n\nSpam ကာကွယ်ရန်အတွက် ကျေးဇူးပြု၍ <b>{time_str}</b> စောင့်ပြီးမှ ထပ်ပို့ပေးပါ။", parse_mode=ParseMode.HTML)
    schedule_delete(context, update.effective_chat.id, warn.message_id, 15)

# ================= ⚙️ ADMIN LIMIT & COOLDOWN SETTINGS =================
async def set_daily_limit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    args = context.args
    if len(args) < 1:
        return await update.message.reply_text("⚠️ အသုံးပြုနည်း: `/setlimit <အရေအတွက်>`\n(ဥပမာ - `/setlimit 3` [တစ်နေ့ ၃ ခုသာ ခွင့်ပြုရန်])", parse_mode=ParseMode.HTML)
    try:
        val = int(args[0])
        db = get_db()
        if db: await db.settings.update_one({"type": "daily_limit"}, {"$set": {"count": val}}, upsert=True)
        status = f"<b>{val} ခု</b>" if val > 0 else "<b>အကန့်အသတ်မရှိ (Unlimited)</b>"
        await update.message.reply_text(f"✅ တစ်နေ့စာ Confession ပို့ခွင့် အကြိမ်အရေအတွက်ကို {status} သို့ သတ်မှတ်လိုက်ပါပြီ。", parse_mode=ParseMode.HTML)
    except ValueError:
        await update.message.reply_text("❌ ဂဏန်းသာ ထည့်ပါ။")

async def set_cooldown_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    db = get_db()
    setting = await db.settings.find_one({"type": "cooldown_limit"})
    current_limit = setting.get("minutes", 0) if setting else 0
    keyboard = [
        [InlineKeyboardButton("🚫 ပိတ်မည် (Off)", callback_data="setcd_0")],
        [InlineKeyboardButton("⏳ 5 Mins", callback_data="setcd_5"), InlineKeyboardButton("⏳ 15 Mins", callback_data="setcd_15"), InlineKeyboardButton("⏳ 30 Mins", callback_data="setcd_30")],
        [InlineKeyboardButton("⏳ 1 Hour", callback_data="setcd_60"), InlineKeyboardButton("⏳ 3 Hours", callback_data="setcd_180"), InlineKeyboardButton("⏳ 6 Hours", callback_data="setcd_360")]
    ]
    await update.message.reply_text(f"⚙️ <b>GLOBAL COOLDOWN SETTINGS</b>\n\nလက်ရှိ: <b>{current_limit} မိနစ်</b>\nအသစ်သတ်မှတ်ရန် အောက်တွင်ရွေးချယ်ပါ:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def set_cooldown_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query.data.startswith("setcd_"): return
    await query.answer()
    try:
        if update.effective_user.id != OWNER_ID: return await query.edit_message_text("⚠️ Admin Only.", parse_mode=ParseMode.HTML)
        val = int(query.data.split('_')[1])
        db = get_db()
        if db is not None: await db.settings.update_one({"type": "cooldown_limit"}, {"$set": {"minutes": val}}, upsert=True)
        status = f"<b>{val} မိနစ်</b>" if val > 0 else "<b>ပိတ်ထားသည် (Off)</b>"
        await query.edit_message_text(f"✅ Global Cooldown အချိန်ကို {status} သို့ ပြောင်းလဲသတ်မှတ်လိုက်ပါပြီ。", parse_mode=ParseMode.HTML)
    except Exception as e:
        await query.edit_message_text(f"❌ Error:\n<pre>{e}</pre>", parse_mode=ParseMode.HTML)

async def set_user_cooldown_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    args = context.args
    if len(args) < 2: return await update.message.reply_text("⚠️ အသုံးပြုနည်း: `/setusercd <User_ID> <Minutes>`", parse_mode=ParseMode.HTML)
    try:
        target_id = int(args[0])
        val = int(args[1])
        db = get_db()
        if db is not None: await db.user_settings.update_one({"user_id": target_id}, {"$set": {"custom_cooldown": val}}, upsert=True)
        status = f"<b>{val} မိနစ်</b>" if val > 0 else "<b>Global ပုံမှန်တိုင်း</b>"
        await update.message.reply_text(f"👤 User <code>{target_id}</code> အတွက် Cooldown ကို {status} အဖြစ် သတ်မှတ်လိုက်ပါပြီ。", parse_mode=ParseMode.HTML)
    except ValueError:
        await update.message.reply_text("❌ User ID နှင့် မိနစ်ကို ဂဏန်းဖြင့်သာ ထည့်ပါ။")

# ================= ⚙️ APPROVERS MANAGEMENT =================
async def approvers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    db = get_db()
    approvers = await db.approvers.find({}).to_list(length=None) if db is not None else []
    kb = []
    for app in approvers: kb.append([InlineKeyboardButton(f"❌ Remove: {app['name']}", callback_data=f"delapp_{app['user_id']}")])
    kb.append([InlineKeyboardButton("➕ Add New Approver", callback_data="addapp_start")])
    kb.append([InlineKeyboardButton("Done", callback_data="cancel_app")])
    await update.message.reply_text("👮‍♂️ <b>APPROVER MANAGEMENT</b>\n<pre>Manage admins who can approve confessions:</pre>", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def approvers_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if update.effective_user.id != OWNER_ID: return await query.answer("⚠️ Owner Only")
    db = get_db()
    
    if data == "cancel_app":
        await query.edit_message_text("<pre>✅ Approver management closed.</pre>", parse_mode=ParseMode.HTML)
        return ConversationHandler.END
        
    if data.startswith("delapp_"):
        uid = int(data.split("_")[1])
        if db is not None: await db.approvers.delete_one({"user_id": uid})
        await query.answer("Removed!")
        approvers = await db.approvers.find({}).to_list(length=None) if db is not None else []
        kb = []
        for app in approvers: kb.append([InlineKeyboardButton(f"❌ Remove: {app['name']}", callback_data=f"delapp_{app['user_id']}")])
        kb.append([InlineKeyboardButton("➕ Add New Approver", callback_data="addapp_start")])
        kb.append([InlineKeyboardButton("Done", callback_data="cancel_app")])
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
        return ConversationHandler.END

    if data == "addapp_start":
        await query.answer()
        await query.edit_message_text("<b>➕ ADD APPROVER</b>\n<pre>Enter the Telegram User ID and Name.\nFormat: ID Name\nExample: 12345678 John</pre>", parse_mode=ParseMode.HTML)
        return APPROVER_ADD

async def add_approver_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().split(maxsplit=1)
    if len(text) < 2:
        await update.message.reply_text("❌ Format အမှား။ ဥပမာ: `12345678 John`", parse_mode=ParseMode.HTML)
        return APPROVER_ADD
    try:
        uid = int(text[0])
        name = text[1]
        db = get_db()
        if db is not None: await db.approvers.update_one({"user_id": uid}, {"$set": {"name": name}}, upsert=True)
        await update.message.reply_text(f"✅ {name} ({uid}) အား Approver အဖြစ် သတ်မှတ်လိုက်ပါပြီ。\n/approvers ကိုနှိပ်၍ ပြန်စစ်ဆေးနိုင်ပါသည်။")
    except ValueError:
        await update.message.reply_text("❌ User ID သည် ဂဏန်းသာဖြစ်ရမည်။")
    return ConversationHandler.END

# ================= 🛡️ DISTRIBUTED ADMIN APPROVAL =================
async def admin_approval_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not (query.data.startswith("aprv_") or query.data.startswith("rjct_")): return
    await query.answer()
    
    action, post_id = query.data.split("_")
    db = get_db()
    if db is None: return
    
    post = await db.pending_posts.find_one_and_delete({"post_id": post_id})
    if not post:
        return await query.edit_message_text(f"{query.message.text}\n\n⚠️ <i>ဤစာအား အခြား Admin တစ်ဦးမှ စိစစ်ပြီးသွားပါပြီ။</i>", parse_mode=ParseMode.HTML)
        
    admin_name = update.effective_user.first_name
    action_text = "APPROVED" if action == "aprv" else "REJECTED"
    
    admin_msgs = post.get("admin_msgs", [])
    for adm in admin_msgs:
        chat_id = adm["chat_id"]
        msg_id = adm["msg_id"]
        try:
            if chat_id == update.effective_user.id:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=f"{query.message.text}\n\n<b>✅ {action_text}</b>", parse_mode=ParseMode.HTML)
            else:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=f"{query.message.text}\n\n⚠️ <i>Action taken by {admin_name} ({action_text})</i>", parse_mode=ParseMode.HTML)
        except: pass

    if LOG_GROUP_ID != 0 and post.get("log_msg_id"):
        try:
            log_txt = f"🚨 <b>SYSTEM LOG | #{'Confession' if 'confess' in post['type'] else 'Notice'}</b>\n🎯 <b>Target:</b> {post['target']}\n👤 <b>User:</b> @{post.get('sender_uname')} (ID: <code>{post['sender_id']}</code>)\n📝 <b>Content:</b>\n<pre>{post['msg']}</pre>\n\n<b>Status:</b> {'✅ APPROVED' if action == 'aprv' else '❌ REJECTED'} by {admin_name}"
            await context.bot.edit_message_text(chat_id=LOG_GROUP_ID, message_id=post["log_msg_id"], text=log_txt, parse_mode=ParseMode.HTML)
        except Exception as e: logger.error(f"Log Update Error: {e}")

    if action == "aprv":
        target = post['target']
        sender_id = post['sender_id']
        
        # 📌 Admin Approved ပြီးလျှင် Sender ၏ Membership အတိုင်းသာ ပို့ပေးမည်
        allowed_groups = await get_allowed_groups(sender_id, context)
        target_ids = allowed_groups if target == "all" else [int(target)]
        
        if post['type'] == 'confess_anon': final_msg = f"<b>#Confession</b>\n<pre>{post['msg']}</pre>\n\n<i>- Anonymous</i>{FOOTER}"
        elif post['type'] == 'confess_custom': final_msg = f"<b>#Confession</b>\n<pre>{post['msg']}</pre>\n\n<i>- {post.get('name', 'Anonymous')}</i>{FOOTER}"
            
        for gid in target_ids:
            try: await context.bot.send_message(chat_id=gid, text=final_msg, parse_mode=ParseMode.HTML)
            except Exception as e: logger.error(f"Failed to send to {gid}: {e}")

# ================= 🏷️ NICKNAME SYSTEM (/nickname) =================
async def nickname_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        try: await update.message.delete()
        except: pass
        warn = await update.message.reply_text("⚠️ DM Access Only.")
        schedule_delete(context, update.effective_chat.id, warn.message_id, 5)
        return ConversationHandler.END
        
    current_id = await get_user_identity(update.effective_user.id)
    
    await update.message.reply_text(
        f"🏷️ <b>NICKNAME SETUP</b>\n<pre>လက်ရှိသုံးနေသော နာမည်/Emoji: {current_id}</pre>\n\nအသစ်ပြောင်းလိုသော Nickname (သို့မဟုတ်) Emoji ကို ရိုက်ထည့်ပါ။\n(ဥပမာ - Shadow, Batman, 👻)\n\n<i>ပယ်ဖျက်လိုပါက /cancel ကိုနှိပ်ပါ။</i>",
        parse_mode=ParseMode.HTML
    )
    return NICK_MSG

async def nickname_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_nick = update.message.text[:20] 
    context.user_data['new_nick'] = new_nick
    
    preview = f"<b>#{new_nick}</b>\n<pre>ဒါကတော့ Notice စာသား နမူနာဖြစ်ပါတယ်။</pre>\n\n<i>- {new_nick}</i>"
    
    kb = [
        [InlineKeyboardButton("✅ SAVE NICKNAME", callback_data="savenick_yes"), InlineKeyboardButton("❌ CANCEL", callback_data="savenick_no")],
        [InlineKeyboardButton("🔄 Reset to Random Emoji", callback_data="savenick_reset")]
    ]
    
    await update.message.reply_text(
        f"👀 <b>PREVIEW (နမူနာကြည့်ရန်)</b>\n\n{preview}\n\nဒီအတိုင်း မှတ်ထားလိုက်ရမလားဗျာ?",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML
    )
    return NICK_CONFIRM

async def nickname_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = get_db()
    
    if query.data == "savenick_yes":
        new_nick = context.user_data.get('new_nick', 'Unknown')
        if db is not None:
            await db.user_settings.update_one({"user_id": update.effective_user.id}, {"$set": {"nickname": new_nick}}, upsert=True)
        await query.edit_message_text(f"✅ သင့်ရဲ့ Nickname အသစ်ကို <b>{new_nick}</b> အဖြစ် အောင်မြင်စွာ မှတ်သားလိုက်ပါပြီ။", parse_mode=ParseMode.HTML)
        
    elif query.data == "savenick_reset":
        if db is not None:
            await db.user_settings.update_one({"user_id": update.effective_user.id}, {"$unset": {"nickname": ""}})
        await query.edit_message_text("✅ ပုံမှန် Random Emoji စနစ်သို့ ပြန်လည်ပြောင်းလဲလိုက်ပါပြီ။", parse_mode=ParseMode.HTML)
        
    else:
        await query.edit_message_text("<pre>🚫 Canceled.</pre>", parse_mode=ParseMode.HTML)
        
    return ConversationHandler.END

# ================= ANONYMOUS CONFESSION (/confess1) =================
async def confess_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        try: await update.message.delete()
        except: pass
        warn = await update.message.reply_text("⚠️ DM Access Only.")
        schedule_delete(context, update.effective_chat.id, warn.message_id, 5)
        return ConversationHandler.END
        
    daily_ok, limit_count = await check_daily_limit(update.effective_user.id)
    if not daily_ok:
        warn = await update.message.reply_text(f"🚫 <b>DAILY LIMIT REACHED</b>\n\nယနေ့အတွက် သတ်မှတ်ထားသော ကန့်သတ်ချက် (<b>{limit_count}</b> ခု) ပြည့်သွားပါပြီ။", parse_mode=ParseMode.HTML)
        schedule_delete(context, update.effective_chat.id, warn.message_id, 15)
        return ConversationHandler.END
        
    remain_sec = await check_user_cooldown(update.effective_user.id)
    if remain_sec > 0:
        await show_cooldown_warning(update, remain_sec, context)
        return ConversationHandler.END

    await update.message.reply_text("<b>🕵️ ANONYMOUS CONFESSION</b>\n<pre>Enter your message (Identity Hidden):</pre>", parse_mode=ParseMode.HTML)
    return CONFESS_MSG

async def confess_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['msg'] = update.message.text
    context.user_data['sender_uname'] = update.effective_user.username or "No_Username"
    context.user_data['send_time'] = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    
    # 📌 ဤနေရာတွင် user_id ကို ပေးပို့၍ membership စစ်ပါသည်
    markup = await build_target_keyboard(update.effective_user.id, context, "send_confess", "cancel_confess")
    await update.message.reply_text(f"<b>📝 VERIFY & SELECT TARGET</b>\n<pre>{update.message.text}</pre>", reply_markup=markup, parse_mode=ParseMode.HTML)
    return CONFESS_CONFIRM

async def confess_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("send_confess"):
        chat_id = query.message.chat_id
        msg_id = query.message.message_id
        user_id = update.effective_user.id
        
        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text="<pre>🤖 သင်၏စာကို AI မှ အကဲဖြတ်နေပါသည်... [■■□□□]</pre>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.8)
        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text="<pre>🤖 သင်၏စာကို AI မှ အကဲဖြတ်နေပါသည်... [■■■■■]</pre>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.6)
        
        target = query.data.replace("send_confess_", "")
        msg = context.user_data.get('msg', '')
        post_id = str(uuid.uuid4())[:8]
        db = get_db()
        log_msg_id = None
        admin_msgs = []
        
        if db is not None:
            if LOG_GROUP_ID != 0:
                log_txt = f"🚨 <b>SYSTEM LOG | #Confession</b>\n🎯 <b>Target:</b> {target}\n👤 <b>User:</b> @{context.user_data.get('sender_uname', '')} (ID: <code>{user_id}</code>)\n📝 <b>Content:</b>\n<pre>{msg}</pre>\n\n⏳ <i>Pending Approval...</i>"
                try: 
                    m = await context.bot.send_message(LOG_GROUP_ID, text=log_txt, parse_mode=ParseMode.HTML)
                    log_msg_id = m.message_id
                except: pass
            
            approvers = await db.approvers.find({}).to_list(length=None)
            approver_ids = [a['user_id'] for a in approvers]
            if OWNER_ID not in approver_ids: approver_ids.append(OWNER_ID)
            
            dm_txt = f"🚨 <b>PENDING CONFESSION</b>\n👤 <b>Telegram ID:</b> <code>{user_id}</code>\n🎯 <b>Target:</b> {target}\n\n📝 <b>Message:</b>\n<pre>{msg}</pre>"
            kb = [[InlineKeyboardButton("✅ APPROVE", callback_data=f"aprv_{post_id}"), InlineKeyboardButton("❌ REJECT", callback_data=f"rjct_{post_id}")]]
            
            for adm_id in approver_ids:
                try:
                    m = await context.bot.send_message(adm_id, text=dm_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
                    admin_msgs.append({"chat_id": adm_id, "msg_id": m.message_id})
                except: pass
                
            await db.pending_posts.insert_one({
                "post_id": post_id, "type": "confess_anon", "msg": msg, "target": target,
                "sender_id": user_id, "sender_uname": context.user_data.get('sender_uname', ''), "time": context.user_data.get('send_time', ''),
                "admin_msgs": admin_msgs, "log_msg_id": log_msg_id
            })
                
        await update_user_cooldown(user_id)
        await increment_daily_limit(user_id)
        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text="<pre>✅ AI အကဲဖြတ်မှု အောင်မြင်ပါသည်။ Admin ထံသို့ ပို့ပြီးပါပြီ。</pre>", parse_mode=ParseMode.HTML)
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
        
    daily_ok, limit_count = await check_daily_limit(update.effective_user.id)
    if not daily_ok:
        warn = await update.message.reply_text(f"🚫 <b>DAILY LIMIT REACHED</b>\n\nယနေ့အတွက် သတ်မှတ်ထားသော ကန့်သတ်ချက် (<b>{limit_count}</b> ခု) ပြည့်သွားပါပြီ။", parse_mode=ParseMode.HTML)
        schedule_delete(context, update.effective_chat.id, warn.message_id, 15)
        return ConversationHandler.END
        
    remain_sec = await check_user_cooldown(update.effective_user.id)
    if remain_sec > 0:
        await show_cooldown_warning(update, remain_sec, context)
        return ConversationHandler.END

    await update.message.reply_text("<b>🎭 CONFESSION SYSTEM (NAME REQUIRED)</b>\n<pre>Enter your confession message:</pre>", parse_mode=ParseMode.HTML)
    return C1_MSG

async def c1_receive_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['c1_msg'] = update.message.text
    await update.message.reply_text("<b>✍️ SIGNATURE</b>\n<pre>Enter the name/signature you want to show (e.g. Ben):</pre>", parse_mode=ParseMode.HTML)
    return C1_NAME

async def c1_receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['c1_name'] = update.message.text
    context.user_data['sender_uname'] = update.effective_user.username or "No_Username"
    context.user_data['send_time'] = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    msg = context.user_data['c1_msg']
    name = context.user_data['c1_name']
    
    # 📌 ဤနေရာတွင် user_id ကို ပေးပို့၍ membership စစ်ပါသည်
    markup = await build_target_keyboard(update.effective_user.id, context, "send_c1", "cancel_c1")
    await update.message.reply_text(f"<b>📝 PREVIEW & SELECT TARGET</b>\n<pre>{msg}</pre>\n\n<i>- {name}</i>", reply_markup=markup, parse_mode=ParseMode.HTML)
    return C1_CONFIRM

async def c1_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("send_c1"):
        chat_id = query.message.chat_id
        msg_id = query.message.message_id
        user_id = update.effective_user.id
        
        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text="<pre>🤖 သင်၏စာကို AI မှ အကဲဖြတ်နေပါသည်... [■■□□□]</pre>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.8)
        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text="<pre>🤖 သင်၏စာကို AI မှ အကဲဖြတ်နေပါသည်... [■■■■■]</pre>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.6)
        
        target = query.data.replace("send_c1_", "")
        msg = context.user_data.get('c1_msg', '')
        name = context.user_data.get('c1_name', 'Anonymous')
        post_id = str(uuid.uuid4())[:8]
        db = get_db()
        log_msg_id = None
        admin_msgs = []
        
        if db is not None:
            if LOG_GROUP_ID != 0:
                log_txt = f"🚨 <b>SYSTEM LOG | #Confession (Custom)</b>\n🎯 <b>Target:</b> {target}\n👤 <b>User:</b> @{context.user_data.get('sender_uname', '')} (ID: <code>{user_id}</code>)\n🎭 <b>Signature:</b> {name}\n📝 <b>Content:</b>\n<pre>{msg}</pre>\n\n⏳ <i>Pending Approval...</i>"
                try: 
                    m = await context.bot.send_message(LOG_GROUP_ID, text=log_txt, parse_mode=ParseMode.HTML)
                    log_msg_id = m.message_id
                except: pass
            
            approvers = await db.approvers.find({}).to_list(length=None)
            approver_ids = [a['user_id'] for a in approvers]
            if OWNER_ID not in approver_ids: approver_ids.append(OWNER_ID)
            
            dm_txt = f"🚨 <b>PENDING CONFESSION (CUSTOM)</b>\n👤 <b>Telegram ID:</b> <code>{user_id}</code>\n🎯 <b>Target:</b> {target}\n🎭 <b>Signature:</b> {name}\n\n📝 <b>Message:</b>\n<pre>{msg}</pre>"
            kb = [[InlineKeyboardButton("✅ APPROVE", callback_data=f"aprv_{post_id}"), InlineKeyboardButton("❌ REJECT", callback_data=f"rjct_{post_id}")]]
            
            for adm_id in approver_ids:
                try:
                    m = await context.bot.send_message(adm_id, text=dm_txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
                    admin_msgs.append({"chat_id": adm_id, "msg_id": m.message_id})
                except: pass
                
            await db.pending_posts.insert_one({
                "post_id": post_id, "type": "confess_custom", "msg": msg, "target": target, "name": name,
                "sender_id": user_id, "sender_uname": context.user_data.get('sender_uname', ''), "time": context.user_data.get('send_time', ''),
                "admin_msgs": admin_msgs, "log_msg_id": log_msg_id
            })
                
        await update_user_cooldown(user_id)
        await increment_daily_limit(user_id)
        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text="<pre>✅ AI အကဲဖြတ်မှု အောင်မြင်ပါသည်။ Admin ထံသို့ ပို့ပြီးပါပြီ。</pre>", parse_mode=ParseMode.HTML)
    else:
        await query.edit_message_text("<pre>🚫 ABORTED.</pre>", parse_mode=ParseMode.HTML)
    return ConversationHandler.END

# ================= NOTICE SYSTEM (/notice) [DIRECT SEND] =================
async def notice_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private':
        try: await update.message.delete()
        except: pass
        warn = await update.message.reply_text("<pre>⚠️ DM Access Only.</pre>", parse_mode=ParseMode.HTML)
        schedule_delete(context, update.effective_chat.id, warn.message_id, 5)
        return ConversationHandler.END
        
    remain_sec = await check_user_cooldown(update.effective_user.id)
    if remain_sec > 0:
        await show_cooldown_warning(update, remain_sec, context)
        return ConversationHandler.END

    await update.message.reply_text("<b>📢 SECURE NOTICE SYSTEM</b>\n<pre>Enter your notice message:</pre>", parse_mode=ParseMode.HTML)
    return NOTICE_MSG

async def notice_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['notice_msg'] = update.message.text
    context.user_data['sender_uname'] = update.effective_user.username or "No_Username"
    context.user_data['send_time'] = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

    # 📌 ဤနေရာတွင် user_id ကို ပေးပို့၍ membership စစ်ပါသည်
    markup = await build_target_keyboard(update.effective_user.id, context, "send_notice", "cancel_notice")
    await update.message.reply_text(
        f"<b>📝 VERIFY & SELECT TARGET</b>\n<pre>{update.message.text}</pre>",
        reply_markup=markup, parse_mode=ParseMode.HTML
    )
    return NOTICE_CONFIRM

async def notice_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        if query.data.startswith("send_notice"):
            target = query.data.replace("send_notice_", "")
            
            # 📌 User ရှိသော Group များကိုသာ စစ်ထုတ်ပါသည်
            allowed_groups = await get_allowed_groups(update.effective_user.id, context)
            target_ids = allowed_groups if target == "all" else [int(target)]
            msg = context.user_data.get('notice_msg', '')
            
            identity = await get_user_identity(update.effective_user.id)
            final_msg = f"<b>#{identity}</b>\n<pre>{msg}</pre>\n\n<i>- {identity}</i>"
            
            for gid in target_ids:
                try: await context.bot.send_message(chat_id=gid, text=final_msg, parse_mode=ParseMode.HTML)
                except Exception as e: logger.error(f"Group {gid} သို့ပို့ရန်အဆင်မပြေပါ: {e}")
            
            if LOG_GROUP_ID != 0:
                log_txt = f"🚨 <b>SYSTEM LOG | #Notice (Direct)</b>\n🎯 <b>Target:</b> {target}\n👤 <b>User:</b> @{context.user_data.get('sender_uname', '')} (ID: <code>{update.effective_user.id}</code>)\n🏷️ <b>Identity:</b> {identity}\n🕒 <b>Time:</b> {context.user_data.get('send_time', '')}\n📝 <b>Content:</b>\n<pre>{msg}</pre>"
                try: await context.bot.send_message(LOG_GROUP_ID, text=log_txt, parse_mode=ParseMode.HTML)
                except: pass
                
            await update_user_cooldown(update.effective_user.id)
            await query.edit_message_text("<pre>✅ NOTICE DELIVERED.</pre>", parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text("<pre>🚫 ABORTED.</pre>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await query.edit_message_text(f"<pre>❌ Error: {e}</pre>", parse_mode=ParseMode.HTML)
    return ConversationHandler.END