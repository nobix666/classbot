import os
import csv
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database.db import get_db

logger = logging.getLogger(__name__)
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

async def auto_delete_job(context: ContextTypes.DEFAULT_TYPE):
    try: await context.bot.delete_message(chat_id=context.job.chat_id, message_id=context.job.data)
    except: pass

def schedule_delete(context, chat_id, msg_id, delay):
    context.job_queue.run_once(auto_delete_job, delay, chat_id=chat_id, data=msg_id)

async def import_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """CSV ဖိုင်မှ ကျောင်းသားစာရင်းကို MongoDB ထဲသို့ သွင်းမည်"""
    if update.effective_user.id != OWNER_ID: return
    if not update.message.reply_to_message or not update.message.reply_to_message.document: 
        await update.message.reply_text("⚠️ ကျေးဇူးပြု၍ CSV ဖိုင်ကို Reply ပြန်ပြီး /import ရိုက်ပါ။")
        return
    
    doc = update.message.reply_to_message.document
    f_path = f"temp_{doc.file_id}.csv"
    f = await context.bot.get_file(doc.file_id)
    await f.download_to_drive(f_path)
    
    db = get_db()
    if db is None: return

    try:
        count = 0
        with open(f_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader, None) 
            for row in reader:
                if len(row) < 3: continue
                try:
                    uid = int(row[0])
                    uname = row[1] if row[1] else None
                    fname = row[2]
                    target_chat = update.effective_chat.id
                    
                    # MongoDB သို့ Group Members များ သိမ်းဆည်းခြင်း
                    await db.group_members.update_one(
                        {"chat_id": target_chat, "user_id": uid},
                        {"$set": {"username": uname, "first_name": fname}},
                        upsert=True
                    )
                    count += 1
                except: continue
        await update.message.reply_text(f"✅ Imported {count} members to Database.")
    except Exception as e: 
        logger.error(e)
    finally:
        if os.path.exists(f_path): os.remove(f_path)

async def mention_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Group ထဲရှိ လူအကုန်လုံးကို Tag တွဲခေါ်မည် (Group Admin များပါ သုံးနိုင်သည်)"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # 1. Group Admin ဟုတ်/မဟုတ် စစ်ဆေးခြင်း
    is_authorized = False
    if user_id == OWNER_ID:
        is_authorized = True
    else:
        try:
            # Group ထဲက Admin စာရင်းကို လှမ်းယူမည်
            admins = await context.bot.get_chat_administrators(chat_id)
            admin_ids = [admin.user.id for admin in admins]
            if user_id in admin_ids:
                is_authorized = True
        except Exception as e:
            logger.error(f"Error getting admins: {e}")

    # Admin မဟုတ်ရင် ဘာမှမလုပ်ဘဲ ရပ်မည်
    if not is_authorized: return

    # User ရိုက်လိုက်သော /mention စာသားကို ဖျက်မည်
    try: await update.message.delete() 
    except: pass
    
    db = get_db()
    if db is None: return
    
    # 2. MongoDB ထဲမှ ထို Group ၏ Members များကို ပြန်ရှာခြင်း
    cursor = db.group_members.find({"chat_id": chat_id})
    members = await cursor.to_list(length=None)
    
    if not members: 
        msg = await context.bot.send_message(chat_id, "⚠️ Database တွင် Member စာရင်း မရှိသေးပါ။ CSV ကို /import အရင်လုပ်ပါ။")
        schedule_delete(context, chat_id, msg.message_id, 10)
        return
    
    # 3. Mention စာသား တည်ဆောက်ပြီး ပို့ခြင်း
    delay = 60 # 60 စက္ကန့်အကြာတွင် ဖျက်မည်
    txt = "<b>🔔 SYSTEM ALERT</b>\n"
    for i, m in enumerate(members):
        txt += f'<a href="tg://user?id={m["user_id"]}">▓</a> '
        if (i+1) % 5 == 0: txt += "\n" # ၅ ယောက်တစ်ကြောင်း ဆင်းမည်
    txt += f"\n<pre>Deleting in {delay}s</pre>"
    
    sent = await context.bot.send_message(chat_id, txt, parse_mode=ParseMode.HTML)
    schedule_delete(context, chat_id, sent.message_id, delay)