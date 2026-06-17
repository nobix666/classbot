import os
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database.db import get_db

logger = logging.getLogger(__name__)
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
MAJORS = ["it", "mc", "archi", "ep", "ec", "me", "civil"] # Routing အတွက် Default List

# ================= 🛡️ Admin & Helpers =================
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

def get_class_groups():
    group_id_str = os.getenv("CLASS_GROUP_ID", "0")
    try:
        return [int(g.strip()) for g in group_id_str.split(",") if g.strip() and g.strip() != "0"]
    except ValueError:
        logger.error("CLASS_GROUP_ID format မှားယွင်းနေပါသည်။")
        return []

# ================= 🗑 Auto Delete Helpers =================
background_tasks = set()

async def delayed_delete_task(bot, chat_id, msg_ids, delay):
    await asyncio.sleep(delay)
    for msg_id in msg_ids:
        try: await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except: pass

def schedule_academic_delete(context, chat_id, msg_ids, delay=60):
    task = asyncio.create_task(delayed_delete_task(context.bot, chat_id, msg_ids, delay))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

# ================= 🔔 ၁၀ မိနစ်ကြိုတင် သတိပေးစနစ် (ROUTING SYSTEM ပါဝင်သည်) =================
async def class_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    if db is None: return

    mm_tz = timezone(timedelta(hours=6, minutes=30))
    now = datetime.now(mm_tz)
    if now.weekday() > 4: return
    current_day = DAYS_OF_WEEK[now.weekday()]

    target_time = now + timedelta(minutes=10)
    target_time_str = target_time.strftime("%H:%M")

    cursor = db.timetable.find({"day": current_day})
    records = await cursor.to_list(length=None)
    if not records: return

    group_ids = get_class_groups()
    if not group_ids: return

    # 📌 Group အလိုက် ခွင့်ပြုထားသော Major များကို DB မှ ကြိုဆွဲထားပါမည်
    group_routes = {}
    for gid in group_ids:
        doc = await db.group_routes.find_one({"group_id": gid})
        # Database တွင် မရှိသေးပါက Default အနေဖြင့် Major အကုန်လုံးကို ဖွင့်ပေးထားမည်
        group_routes[gid] = doc.get("majors", MAJORS) if doc else MAJORS

    reminders_to_send = {}
    
    for record in records:
        major_name = record.get("major", "ALL").upper()
        if "periods" not in record: continue
        
        for p in record["periods"]:
            start_time = p["time"].split("-")[0].strip()
            if start_time == target_time_str:
                key = (p["subject"], p["teacher"], p["room"])
                if key not in reminders_to_send: reminders_to_send[key] = []
                if major_name not in reminders_to_send[key]: reminders_to_send[key].append(major_name)

    for (subject, teacher, room), class_majors in reminders_to_send.items():
        tag = " <code>[ALL]</code>" if "ALL" in class_majors else f" <code>[{', '.join(class_majors)}]</code>"
        msg = f"🔔 <b>အတန်းစရန် (၁၀) မိနစ်သာ လိုပါတော့သည်!</b>\n\n📚 <b>ဘာသာရပ်:</b> {subject}{tag}\n👨‍🏫 <b>ဆရာ/မ:</b> {teacher}\n🏫 <b>အခန်း:</b> {room}"
        
        for gid in group_ids:
            allowed_majors = group_routes.get(gid, [])
            should_send = False
            
            # 📌 အတန်းချိန်သည် ALL ဖြစ်လျှင် သို့မဟုတ် Group ၏ ခွင့်ပြုစာရင်းထဲတွင် ထို Major ပါဝင်လျှင် ပို့မည်
            if "ALL" in class_majors:
                should_send = True
            else:
                for m in class_majors:
                    if m.lower() in allowed_majors:
                        should_send = True
                        break
            
            if should_send:
                try:
                    sent_msg = await context.bot.send_message(chat_id=gid, text=msg, parse_mode=ParseMode.HTML)
                    schedule_academic_delete(context, gid, [sent_msg.message_id], 600)
                except: pass

# ================= 📅 TIMETABLE VIEW =================
async def build_timetable_message(major: str, day_idx: int):
    day_name = DAYS_OF_WEEK[day_idx]
    db = get_db()
    
    text = f"📅 <b>{major.upper()} TIMETABLE - {day_name}</b>\n━━━━━━━━━━━━━━━━━━\n"
    has_class = False
    
    if db is not None:
        cursor = db.timetable.find({
            "day": day_name, 
            "major": {"$in": [major.lower(), "all"]}
        })
        records = await cursor.to_list(length=None)
        
        all_periods = []
        for record in records:
            if "periods" in record:
                all_periods.extend(record["periods"])
                
        all_periods.sort(key=lambda x: x["time"])

        for p in all_periods:
            has_class = True
            text += f"⏰ <b>{p['time']}</b>\n"
            text += f"📚 Subject: {p['subject']}\n"
            text += f"👨‍🏫 Teacher: {p['teacher']}\n"
            text += f"🏫 Room: {p['room']}\n\n"
                
    if not has_class:
        text += "🎉 <i>ဒီနေ့အတွက် အတန်းမရှိပါ။ (Free Day)</i>\n"

    prev_idx = (day_idx - 1) % 5
    next_idx = (day_idx + 1) % 5
    keyboard = [[
        InlineKeyboardButton("⬅️", callback_data=f"tt_{major}_{prev_idx}"),
        InlineKeyboardButton(day_name[:3], callback_data="ignore"),
        InlineKeyboardButton("➡️", callback_data=f"tt_{major}_{next_idx}")
    ]]
    return text, InlineKeyboardMarkup(keyboard)

async def get_timetable_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_msg_id = update.message.message_id
    
    cmd = update.message.text.split()[0].lower().replace('/', '')
    major = cmd.upper()
    
    mm_tz = timezone(timedelta(hours=6, minutes=30))
    now = datetime.now(mm_tz)
    
    day_idx = now.weekday()
    
    if now.hour >= 16:
        day_idx += 1
        
    if day_idx > 4:
        day_idx = 0
    
    text, markup = await build_timetable_message(major, day_idx)
    sent = await update.message.reply_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    schedule_academic_delete(context, chat_id, [user_msg_id, sent.message_id], 60)

async def change_timetable_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "ignore": return await query.answer()
    
    _, major, day_idx_str = query.data.split('_')
    day_idx = int(day_idx_str)
    
    text, markup = await build_timetable_message(major, day_idx)
    try:
        await query.edit_message_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    except: pass
    await query.answer()

# ================= 📝 TASKS & TUTORIALS VIEW =================
async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_msg_id = update.message.message_id
    cmd = update.message.text.split()[0].lower()
    task_type = "Tutorial" if "tutorial" in cmd else "Assignment"
    
    db = get_db()
    if db is None: return
    
    cursor = db.tasks.find({"type": task_type}).sort("deadline", 1)
    tasks = await cursor.to_list(length=100)
    title = "📝 <b>ASSIGNMENTS & TASKS</b>" if task_type == "Assignment" else "📚 <b>TUTORIALS & EXAMS</b>"
    
    if not tasks:
        msg = f"{title}\n━━━━━━━━━━━━━━━━━━\n🎉 <b>ဘာမှမရှိသေးဘူး။ ဘာလဲ စာလုပ်ချင်လို့လား။</b>"
        sent = await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        schedule_academic_delete(context, chat_id, [user_msg_id, sent.message_id], 60)
        return
        
    msg = f"{title}\n━━━━━━━━━━━━━━━━━━\n"
    for idx, t in enumerate(tasks, 1):
        msg += f"{idx}. 📌 <b>{t['title']}</b>\n"
        msg += f"   🏷️ Major: <code>{t['major']}</code>\n"
        msg += f"   📅 Deadline: <code>{t['deadline']}</code>\n\n"
        
    sent = await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    schedule_academic_delete(context, chat_id, [user_msg_id, sent.message_id], 60)

# ================= ⚙️ ADMIN MANAGEMENT =================
async def add_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_check(update, context): return
    args = context.args
    if len(args) < 6: return await update.message.reply_text("⚠️ `/addclass <Day> <Time> <Major> <Room> <Teacher> <Subject>`", parse_mode=ParseMode.HTML)
    
    day, time, major, room, teacher, subject = args[0], args[1], args[2], args[3], args[4], " ".join(args[5:])
    db = get_db()
    if db is None: return
    
    period = {"time": time, "room": room, "teacher": teacher, "subject": subject}
    await db.timetable.update_one(
        {"day": day, "major": major.lower()}, 
        {"$push": {"periods": period}}, 
        upsert=True
    )
    await update.message.reply_text(f"✅ {day} တွင် <b>{major.upper()}</b> အတွက် အတန်းချိန်အသစ် သွင်းပြီးပါပြီ。", parse_mode=ParseMode.HTML)

async def del_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_check(update, context): return
    args = context.args
    if len(args) < 3: return await update.message.reply_text("⚠️ `/delclass <Day> <Time> <Major>`", parse_mode=ParseMode.HTML)
    
    db = get_db()
    if db is None: return
    
    await db.timetable.update_one(
        {"day": args[0], "major": args[2].lower()}, 
        {"$pull": {"periods": {"time": args[1]}}}
    )
    await update.message.reply_text(f"🗑️ {args[0]} မှ {args[1]} ({args[2].upper()}) အတန်းကို ဖျက်လိုက်ပါပြီ။")

async def clear_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_check(update, context): return
    if len(context.args) < 2: return await update.message.reply_text("⚠️ အသုံးပြုနည်း: `/clearday <Day> <Major>`", parse_mode=ParseMode.HTML)
    
    day = context.args[0]
    major = context.args[1]
    
    db = get_db()
    if db is None: return
    
    await db.timetable.update_one(
        {"day": day, "major": major.lower()}, 
        {"$set": {"periods": []}}
    )
    await update.message.reply_text(f"🧹 {day} ၏ <b>{major.upper()}</b> အတန်းချိန်အားလုံးကို ရှင်းလင်းလိုက်ပါပြီ。", parse_mode=ParseMode.HTML)

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_check(update, context): return
    args = context.args
    if len(args) < 4: return await update.message.reply_text("⚠️ `/addtask <Type> <Major> <Deadline> <Title>`", parse_mode=ParseMode.HTML)
    
    task_type, major, deadline, title = args[0], args[1], args[2], " ".join(args[3:])
    db = get_db()
    if db is None: return
    
    await db.tasks.insert_one({"type": task_type, "major": major, "deadline": deadline, "title": title})
    await update.message.reply_text("✅ Task/Tutorial အသစ် မှတ်သားပြီးပါပြီ။")