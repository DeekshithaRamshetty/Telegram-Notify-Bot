# 🤖 Telegram Todo Bot

A smart Telegram bot that helps you manage tasks with intelligent reminders and scheduling features.

## ✨ Features

- **Task Management**: Add, view, and delete tasks
- **Smart Reminders**: Automatic notifications 30 minutes before due time
- **Task Types**: 
  - Day Tasks (with specific time)
  - Week Tasks (by day of week)
- **Interactive Reminders**: Mark tasks as done or reschedule them
- **Natural Language**: Responds to "hi", "hello", "thank you"
- **Persistent Storage**: Tasks saved between bot restarts

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/DeekshithaRamshetty/Telegram-Notify-Bot.git
   cd Telegram-Notify-Bot
   ```

2. **Install dependencies**
   ```bash
   pip install python-telegram-bot pytz
   ```

3. **Set up your bot token**
   - Create a bot with [@BotFather](https://t.me/botfather)
   - Replace `YOUR_BOT_TOKEN_HERE` in `main.py` with your token

4. **Run the bot**
   ```bash
   python main.py
   ```

## 💬 How to Use

### Commands
- `/start` - Welcome message and instructions
- `/addtask` - Add a new task
- `/viewtasks` - View all your tasks
- `/deletetask` - Delete a task
- `/cancel` - Cancel current operation

### Natural Interactions
- Say "hi", "hello", or "hey" to get the main menu
- Say "thank you" to get a polite goodbye

### Task Types
1. **Day Task**: Set a specific time (e.g., 14:30)
2. **Week Task**: Choose a day of the week

## 🔔 Reminder System

- **30-minute warning**: Get notified 30 minutes before task time
- **Immediate alerts**: For tasks due within 30 minutes
- **At-time reminders**: Final notification when task is due
- **Interactive options**: Mark as done or reschedule

### Reschedule Options
- 30 minutes
- 1 hour
- 2 hours
- Tomorrow

## 🛠️ Technical Details

- **Language**: Python 3.7+
- **Framework**: python-telegram-bot v20+
- **Timezone**: Asia/Kolkata (configurable)
- **Storage**: Pickle persistence for data retention

## 📁 Project Structure

```
├── main.py          # Main bot application
├── .gitignore       # Git ignore file
└── README.md        # This file
```

## 🔧 Configuration

Change timezone in `main.py`:
```python
TIMEZONE = pytz.timezone('Your/Timezone')  # Default: Asia/Kolkata
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

This project is open source and available under the MIT License.

## 👨‍💻 Author

Created by [Deekshitha Ramshetty](https://github.com/DeekshithaRamshetty)

---

⭐ Star this repo if you found it helpful!