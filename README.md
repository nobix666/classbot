# 🟢 OMNI-NET TERMINAL V3.0 (Class Management Bot)

> *"Everything is a system. Everyone is a variable."* > **System Administered by: The Architect (Ben)**

Omni-Net Terminal (Code Name: Plumber) is an advanced, aesthetic, and multi-functional Telegram Bot designed specifically for university class management, automated reminders, and student social networking. Built with `python-telegram-bot` and MongoDB, it features an interactive HUD-style UI, auto-deleting messages to prevent chat clutter, and a smart multi-group routing system.

---

## 🌟 Core Features

### 🎓 1. Academic Core
* **Smart Class Reminders:** Automatically sends a reminder 10 minutes before class. Uses "Smart Merge" to combine identical classes across different majors (e.g., `[IT, EP]`) into a single clean message.
* **Timetable Management:** Fetch daily schedules for 7 distinct majors via simple commands (`/it`, `/ec`, `/civil`, etc.).
* **Assignments & Tasks:** Track deadlines for tutorials and assignments seamlessly with `/tasks`.

### 💬 2. Social Hub (Multi-Group Support)
* **Direct Message Confessions:** Interactive Conversation Handler in the bot's DM for submitting confessions.
* **Named & Anonymous Mode:** Choose to reveal a custom signature (`/confess`) or stay completely hidden (`/confess1`).
* **Secure Broadcasting:** Admins can broadcast official announcements (`/notice`) across multiple class groups simultaneously.
* **Log System:** All submissions are mirrored to a secure Admin Log Group.

### 🛠️ 3. Utility Node & Admin Console
* **System Telemetry:** Live server stats including CPU load, RAM usage, Uptime, and simulated Latency/Network Speed (`/status`).
* **Tools:** Built-in Base64 Encrypt/Decrypt and Hex/Binary converters.
* **Admin Controls:** Easily manage database entries natively from Telegram (`/addclass`, `/clearday`, `/addtask`, `/addwifi`).

---

## ⚙️ Tech Stack

* **Language:** Python 3.9+
* **Framework:** `python-telegram-bot` (v20+)
* **Database:** MongoDB (Motor Asyncio)
* **Hosting / Process Manager:** PM2 (Node.js)
* **Hardware Monitoring:** `psutil`

---

## 🚀 Installation & Deployment

### 1. Clone the Repository

git clone [https://github.com/YourUsername/YourRepoName.git](https://github.com/YourUsername/YourRepoName.git)
cd YourRepoName


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
