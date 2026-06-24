import os
import re
from datetime import datetime, timezone, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database.db import get_db

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# ================= 💰 ရန်ပုံငွေ အသစ်ဖန်တီးရန် (/newfund) =================
async def newfund_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """အသုံးပြုနည်း: /newfund <FundID> <TargetAmount> [Fund Name]"""
    if update.effective_user.id != OWNER_ID: return
    args = context.args
    if len(args) < 2:
        return await update.message.reply_text("⚠️ <b>အသုံးပြုနည်း:</b> <code>/newfund &lt;FundID&gt; &lt;TargetAmount&gt; [Fund Name]</code>", parse_mode=ParseMode.HTML)
    
    fund_id = args[0].lower()
    try:
        target = int(args[1])
    except ValueError:
        return await update.message.reply_text("❌ ငွေပမာဏ (TargetAmount) ကို ဂဏန်းဖြင့်သာ ထည့်ပါ။")
        
    fund_name = " ".join(args[2:]) if len(args) > 2 else fund_id

    db = get_db()
    await db.funds.update_one(
        {"fund_id": fund_id},
        {"$set": {"target_amount": target, "fund_name": fund_name}},
        upsert=True
    )
    await update.message.reply_text(f"✅ <b>ရန်ပုံငွေအသစ် ဖန်တီး/ပြင်ဆင်ပြီးပါပြီ။</b>\n\n📌 ID: <code>{fund_id}</code>\n🎯 Target: {target} MMK\n🏷️ အမည်: {fund_name}", parse_mode=ParseMode.HTML)

# ================= 🗑 ရန်ပုံငွေ ဖျက်ရန် (/delfund) =================
async def delfund_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """အသုံးပြုနည်း: /delfund <FundID>"""
    if update.effective_user.id != OWNER_ID: return
    if not context.args:
        return await update.message.reply_text("⚠️ <b>အသုံးပြုနည်း:</b> <code>/delfund &lt;FundID&gt;</code>", parse_mode=ParseMode.HTML)
        
    fund_id = context.args[0].lower()
    db = get_db()
    res = await db.funds.delete_one({"fund_id": fund_id})
    
    if res.deleted_count:
        await update.message.reply_text(f"🗑️ ရန်ပုံငွေ <code>{fund_id}</code> ကို ဖျက်လိုက်ပါပြီ။", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"⚠️ <code>{fund_id}</code> အမည်ဖြင့် ရန်ပုံငွေ မရှိပါ။", parse_mode=ParseMode.HTML)

# ================= 💰 ငွေသွင်းစာရင်း မှတ်ရန် (/pay) =================
async def payfund_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """အသုံးပြုနည်း: /pay <RollNo_Last_Digits> <FundID> <Amount>"""
    if update.effective_user.id != OWNER_ID: return
    
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "⚠️ <b>အသုံးပြုနည်း မှားယွင်းနေပါသည်။</b>\n<pre>/pay &lt;RollNo&gt; &lt;FundID&gt; &lt;Amount&gt;</pre>\n(ဥပမာ - <code>/pay 01 sports 2000</code>)", 
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        roll_query = args[0]
        fund_id = args[1].lower()
        amount = int(args[2])
        
        db = get_db()
        regex_pattern = re.compile(re.escape(roll_query) + "$", re.IGNORECASE)
        student = await db.student_info.find_one({"roll_no": regex_pattern})
        
        if not student:
            await update.message.reply_text(f"⚠️ <code>{roll_query}</code> ဖြင့်ဆုံးသော ကျောင်းသားကို ရှာမတွေ့ပါ။", parse_mode=ParseMode.HTML)
            return
            
        current_paid = student.get("paid_funds", {}).get(fund_id, 0)
        new_paid = current_paid + amount
        
        # 📌 မြန်မာစံတော်ချိန်ဖြင့် ငွေသွင်းသည့် ရက်စွဲနှင့် အချိန်ကို မှတ်သားခြင်း
        mm_tz = timezone(timedelta(hours=6, minutes=30))
        current_date = datetime.now(mm_tz).strftime("%d-%b-%Y %I:%M %p")
        
        # သွင်းငွေနှင့် အချိန်မှတ်တမ်းကို DB သို့ ထည့်သွင်းခြင်း
        await db.student_info.update_one(
            {"_id": student["_id"]},
            {
                "$set": {
                    f"paid_funds.{fund_id}": new_paid,
                    "last_payment_date": current_date
                },
                "$push": {
                    "payment_history": {
                        "fund_id": fund_id,
                        "amount": amount,
                        "date": current_date
                    }
                }
            }
        )
        
        await update.message.reply_text(
            f"✅ <b>စာရင်းသွင်းပြီးပါပြီ။</b>\n\n"
            f"👤 ကျောင်းသား: {student.get('name')} ({student.get('roll_no')})\n"
            f"📥 ယခုသွင်းငွေ: {amount} MMK\n"
            f"💰 စုစုပေါင်း သွင်းထားငွေ: {new_paid} MMK\n"
            f"🕒 အချိန်: <code>{current_date}</code>", 
            parse_mode=ParseMode.HTML
        )
    except ValueError:
        await update.message.reply_text("❌ ငွေပမာဏကို ဂဏန်းဖြင့်သာ ထည့်ပါ။")

# ================= ⏪ မှားထည့်မိသည်ကို ပြန်ရုပ်သိမ်းရန် (/undo) =================
async def undo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """အသုံးပြုနည်း: /undo <RollNo_Last_Digits> <FundID>"""
    if update.effective_user.id != OWNER_ID: return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "⚠️ <b>အသုံးပြုနည်း မှားယွင်းနေပါသည်။</b>\n<pre>/undo &lt;RollNo&gt; &lt;FundID&gt;</pre>\n(ဥပမာ - <code>/undo 01 sports</code>)", 
            parse_mode=ParseMode.HTML
        )
        return

    roll_query = args[0]
    fund_id = args[1].lower()

    db = get_db()
    regex_pattern = re.compile(re.escape(roll_query) + "$", re.IGNORECASE)
    student = await db.student_info.find_one({"roll_no": regex_pattern})

    if not student:
        return await update.message.reply_text(f"⚠️ <code>{roll_query}</code> ဖြင့်ဆုံးသော ကျောင်းသားကို ရှာမတွေ့ပါ။", parse_mode=ParseMode.HTML)

    history = student.get("payment_history", [])
    
    # ထိုရန်ပုံငွေအတွက် နောက်ဆုံးသွင်းခဲ့သော မှတ်တမ်းများကို ရှာဖွေခြင်း
    fund_history = [h for h in history if h.get("fund_id") == fund_id]

    if not fund_history:
        return await update.message.reply_text(f"⚠️ <b>{fund_id}</b> အတွက် ပြန်ရုပ်သိမ်းစရာ ငွေသွင်းမှတ်တမ်း မရှိပါ။", parse_mode=ParseMode.HTML)

    # နောက်ဆုံးသွင်းခဲ့သော ငွေပမာဏကို ဆွဲထုတ်ခြင်း
    last_tx = fund_history[-1]
    revert_amount = last_tx["amount"]
    tx_date = last_tx["date"]

    current_paid = student.get("paid_funds", {}).get(fund_id, 0)
    new_paid = max(0, current_paid - revert_amount) # အနှုတ်မပြစေရန် ကာကွယ်ခြင်း

    # နောက်ဆုံးမှတ်တမ်းအား History ထဲမှ ဖယ်ရှားခြင်း
    history.reverse()
    for item in history:
        if item.get("fund_id") == fund_id and item.get("amount") == revert_amount:
            history.remove(item)
            break
    history.reverse()

    await db.student_info.update_one(
        {"_id": student["_id"]},
        {
            "$set": {
                f"paid_funds.{fund_id}": new_paid,
                "payment_history": history
            }
        }
    )

    await update.message.reply_text(
        f"⏪ <b>လုပ်ဆောင်ချက် ပြန်လည်ရုပ်သိမ်းပြီးပါပြီ (Undo Successful)</b>\n━━━━━━━━━━━━━━━━━━\n"
        f"👤 ကျောင်းသား: {student.get('name')} ({student.get('roll_no')})\n"
        f"🗑 ဖျက်လိုက်သော သွင်းငွေ: <b>{revert_amount} MMK</b> <i>(သွင်းခဲ့သည့်အချိန်: {tx_date})</i>\n"
        f"💰 ယခု ကျန်ရှိငွေ: <b>{new_paid} MMK</b>",
        parse_mode=ParseMode.HTML
    )

# ================= 📱 Phone & TG Username (Admin Manual Set) =================
async def setphone_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """အသုံးပြုနည်း: /setphone <RollNo> <Phone>"""
    if update.effective_user.id != OWNER_ID: return
    if len(context.args) < 2: return await update.message.reply_text("⚠️ <b>အသုံးပြုနည်း:</b> <code>/setphone &lt;RollNo&gt; &lt;Phone&gt;</code>", parse_mode=ParseMode.HTML)
    
    roll_query = context.args[0]
    phone = context.args[1]
    db = get_db()
    regex_pattern = re.compile(re.escape(roll_query) + "$", re.IGNORECASE)
    res = await db.student_info.update_one({"roll_no": regex_pattern}, {"$set": {"phone": phone}})
    if res.modified_count:
        await update.message.reply_text("✅ ဖုန်းနံပါတ် ထည့်သွင်း/ပြင်ဆင်ပြီးပါပြီ။")
    else:
        await update.message.reply_text("❌ ကျောင်းသား ရှာမတွေ့ပါ။")

async def settg_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """အသုံးပြုနည်း: /settg <RollNo> <Username>"""
    if update.effective_user.id != OWNER_ID: return
    if len(context.args) < 2: return await update.message.reply_text("⚠️ <b>အသုံးပြုနည်း:</b> <code>/settg &lt;RollNo&gt; &lt;Username&gt;</code>", parse_mode=ParseMode.HTML)
    
    roll_query = context.args[0]
    username = context.args[1].replace("@", "")
    db = get_db()
    regex_pattern = re.compile(re.escape(roll_query) + "$", re.IGNORECASE)
    res = await db.student_info.update_one({"roll_no": regex_pattern}, {"$set": {"tg_username": username}})
    if res.modified_count:
        await update.message.reply_text("✅ Telegram Username ထည့်သွင်း/ပြင်ဆင်ပြီးပါပြီ။")
    else:
        await update.message.reply_text("❌ ကျောင်းသား ရှာမတွေ့ပါ။")