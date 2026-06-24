# 🟢 OMNI-NET TERMINAL V3.1 (My Class Bot)

> *"Everything is a system. Everyone is a variable."* > **Built by a 1st-year IT student trying to survive college: The Architect (Ben)**

Hey guys! I built Omni-Net (Code Name: Plumber) because our class group chat was getting way too messy. Trying to find the timetable, tutorial deadlines, or announcements among 500 stickers is a total nightmare. So, I coded this Telegram bot using Python and MongoDB to handle all the boring class management stuff for us. It also cleans up after itself (auto-delete) so it doesn't spam the group. 

Welcome to V3.1, where we finally automated the class treasurer's suffering!

---

## 🌟 What can it do? (Core Features)

### 🎓 1. Academic Stuff (Lifesavers)
* **Class Reminders:** It literally texts the group 10 minutes before class starts so we don't sleep through it. It even combines majors if we share a class (e.g., `[IT, EP]`).
* **Timetable Check:** Just type `/it`, `/ec`, etc., and it drops the timetable for the day. No more scrolling up to find the pinned photo!
* **Tasks & Tutorials:** Type `/tasks` or `/tutorials` to see what we are procrastinating on. **Update:** It now actively hunts us down (sends auto-reminders 3 days or 18 hours before deadlines) so nobody can say "I forgot".
* **Smart Roll Call:** ECs can generate a random 6-digit PIN in class (`/attendance`), and we just type `/rollcall` in the bot's DM to mark attendance. Less paperwork for everyone.
* **75% Survival Calculator:** Type `/skip` to calculate exactly how many more classes you can safely ditch without getting debarred. You're welcome.

### 💰 2. Class Fund Management (Treasurer's Best Friend)
* **Smart Ledger:** Admins can log payments (`/pay`), view the entire stash (`/vault`), or fix fat-finger mistakes (`/undo`). 
* **Excel Reports on Demand:** Type `/exportfund sports` and the bot spits out a beautiful Excel (`.xlsx`) sheet. It automatically color-codes everyone into 🟢 Paid or 🔴 Unpaid and sorts them.
* **Auto-Debt Collector:** Type `/remind sports` and the bot will automatically DM everyone who hasn't paid yet. No more awkward begging in the main group chat.

### 💬 3. Social Hub (For the Tea)
* **Confessions:** Got a crush or wanna rant? Drop a message in the bot's DM. You can put a fake name/signature (`/confess`), go full ghost mode (`/confess1`), or set a persistent `/nickname`.
* **Notices:** Direct line for announcements (`/notice`) to be broadcasted to all linked class groups.
* **Log System:** Admins have a secret log group to monitor the system, so don't try to spam or break the bot. We see you 👀.

### 🛠️ 4. Geeky Admin Tools & Utilities
* **Hmawbi Weather:** Type `/weather` to see if we're going to melt or get soaked in Hmawbi today. It auto-cleans itself after 60 seconds.
* **System Status:** Type `/status` to see if the VPS is struggling or still breathing (RAM/CPU/Uptime checks).
* **Crypto Tools:** Send `/encrypt` or `/hex2bin` if you want to send secret messages to your friends.

---

## ⚙️ Tech Stack (How I built it)

* **Language:** Python 3.9+ (because I'm an IT major, obviously)
* **Framework:** `python-telegram-bot` (v20+)
* **Database:** MongoDB (Motor Asyncio) - NoSQL saved me so much headache when adding new features.
* **Data Processing:** `openpyxl` (for that sweet Excel wizardry)
* **Hosting:** Running 24/7 on a VPS using PM2 (Node.js).


---

## 🚀 Installation & Deployment

### 1. Clone the Repository

git clone https://github.com/nobix666/classbot.git

cd classbot


### 2. Install Dependencies
pip install -r requirements.txt

### 3. Environment Variables Setup (.env)
Create a .env file in the root directory and configure the following:
BOT_TOKEN=your_telegram_bot_token
MONGO_URI=your_mongodb_connection_string
OWNER_ID=your_personal_telegram_id

# Supports multiple groups by separating IDs with commas
CLASS_GROUP_ID=-100111111111, -100222222222
LOG_GROUP_ID=-100333333333

### 4. Run the Bot (Using PM2 for 24/7 Uptime)
pm2 start main.py --name "plumber" --interpreter python3
pm2 save

## 💡 Usage Highlights
* **Type /start to boot up the Omni-Net Terminal and access the interactive interactive UI.
* **Auto-Delete Mechanism: To keep group chats clean, academic commands and start menus auto-delete after 60 seconds to 5 minutes.
* **Access Clearance: Standard users trying to access the Admin Console will receive a strict Level 9 Clearance Required error.
* **Created and maintained by Ben (The Architect)
