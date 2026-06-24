import os
import re
from uuid import uuid4
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database.db import get_db

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

async def inline_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline Query ဖြင့် ကျောင်းသား ရှာဖွေသည့် စနစ်"""
    query = update.inline_query.query.strip()
    user_id = update.inline_query.from_user.id

    # 📌 Admin ဖြစ်မှသာ ရှာခွင့်ပေးမည်
    if user_id != OWNER_ID:
        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="⛔ Access Denied",
                description="Admin Only Feature",
                input_message_content=InputTextMessageContent("⛔ <b>Access Denied:</b> Level 9 Clearance Required.", parse_mode=ParseMode.HTML)
            )
        ]
        await update.inline_query.answer(results, cache_time=0)
        return

    if not query:
        return

    db = get_db()
    if db is None: return

    # 📌 နာမည် (သို့) Roll No နောက်ဆုံးဂဏန်း ဖြင့် Regex သုံး၍ ရှာခြင်း (Case Insensitive)
    regex_pattern = re.compile(re.escape(query), re.IGNORECASE)
    students = await db.student_info.find({
        "$or": [{"name": regex_pattern}, {"roll_no": regex_pattern}]
    }).to_list(length=10)

    # 📌 လက်ရှိ ကောက်ခံနေသော ရန်ပုံငွေ အားလုံးကို ဆွဲထုတ်ခြင်း (Error မတက်အောင် စစ်ထုတ်ထားသည်)
    funds = await db.funds.find({}).to_list(length=None)
    fund_map = {
        f["fund_id"]: {
            "name": f.get("fund_name", "Unknown Fund"), 
            "target": f.get("target_amount", 0)
        } 
        for f in funds if "fund_id" in f
    }

    results = []
    for s in students:
        name = s.get("name", "Unknown")
        roll_no = s.get("roll_no", "Unknown")
        stu_id = s.get("student_id", "Unknown")
        phone = s.get("phone", "➖")
        hostel = "✅ အဆောင်နေ" if s.get("hostel") else "❌ အပြင်နေ"

        paid_funds = s.get("paid_funds", {})
        tg_id = s.get("tg_id")
        tg_username = s.get("tg_username")

        # 💬 Telegram လင့်ခ် ဖန်တီးခြင်း (Username ရှိလျှင် @ ပြမည်၊ မရှိလျှင် Profile Link ပြမည်)
        if tg_username:
            tg_link = f"\n💬 <b>Telegram:</b> @{tg_username}"
        elif tg_id:
            tg_link = f"\n💬 <b>Telegram:</b> <a href='tg://user?id={tg_id}'>Profile သို့ သွားရန်</a>"
        else:
            tg_link = ""

        # 💰 ရန်ပုံငွေ စာသား တည်ဆောက်ခြင်း
        fund_text = "💰 <b>[ ရန်ပုံငွေ အခြေအနေ ]</b>\n"
        if not fund_map:
            fund_text += "လောလောဆယ် ကောက်ခံနေသော ရန်ပုံငွေ မရှိပါ။\n"
        else:
            for fid, fdata in fund_map.items():
                target = fdata["target"]
                paid = paid_funds.get(fid, 0)
                if paid >= target: status = "✅ အပြည့်သွင်းပြီး"
                elif paid > 0: status = f"⚠️ {target - paid} ကျပ် လိုသေးသည်"
                else: status = "❌ မသွင်းရသေးပါ"
                
                fund_text += f"🔹 <b>{fdata['name']}:</b> {paid} / {target} MMK ({status})\n"

        # 📄 Final Message (နှိပ်လိုက်လျှင် ပို့မည့်စာ)
        msg = (
            f"👤 <b>Name:</b> {name}\n"
            f"🎓 <b>Student ID:</b> {stu_id}\n"
            f"🏷 <b>Roll No:</b> {roll_no}\n"
            f"🏠 <b>Hostel:</b> {hostel}\n"
            f"📞 <b>Phone:</b> <code>{phone}</code>"
            f"{tg_link}\n\n"
            f"{fund_text}"
        )

        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title=f"{name} ({roll_no})",
                description=f"Phone: {phone} | Hostel: {'Yes' if s.get('hostel') else 'No'}",
                input_message_content=InputTextMessageContent(msg, parse_mode=ParseMode.HTML)
            )
        )

    if not results:
        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="⚠️ ရှာမတွေ့ပါ",
                description="ကျောင်းသား အမည် သို့မဟုတ် ခုံနံပါတ် အမှားဖြစ်နိုင်ပါသည်။",
                input_message_content=InputTextMessageContent("⚠️ <b>ရှာဖွေမှုရလဒ် မရှိပါ</b>", parse_mode=ParseMode.HTML)
            )
        )

    await update.inline_query.answer(results, cache_time=0)

# ================= 🧪 စမ်းသပ်ရန် Dummy Data သွင်းမည့် Command =================
async def add_dummy_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    db = get_db()
    
    # ရန်ပုံငွေ အတု ထည့်ခြင်း
    await db.funds.update_one({"fund_id": "fresher"}, {"$set": {"fund_name": "Fresher Welcome", "target_amount": 10000}}, upsert=True)
    await db.funds.update_one({"fund_id": "sports"}, {"$set": {"fund_name": "Sports Event", "target_amount": 5000}}, upsert=True)
    
    # ကျောင်းသား အတု ထည့်ခြင်း
    await db.student_info.update_one(
        {"roll_no": "Sem-II-CEIT-01"},
        {"$set": {
            "name": "John John", "student_id": "TUHmb-25U/00123", "phone": "09123456789", "hostel": True,
            "tg_id": 123456789, "tg_username": "john_doe",
            "paid_funds": {"fresher": 5000, "sports": 0}
        }},
        upsert=True
    )
    await update.message.reply_text("✅ စမ်းသပ်ရန် John John ၏ Data များကို Database ထဲသို့ ထည့်သွင်းပြီးပါပြီ။")