import logging
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ConversationHandler,
    ContextTypes,
    PicklePersistence,
)
import datetime
import pytz

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
TASK_TYPE, DAY_DESC, DAY_TIME, WEEK_DESC, WEEK_DAY = range(5)

# Timezone setup
TIMEZONE = pytz.timezone('Asia/Kolkata')  # Change to your timezone

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(
        f"Hi {user.first_name}! I'm your Todo Bot. I'll help you manage your tasks.\n\n"
        "Use /addtask to add a new task\n"
        "Use /viewtasks to see your current tasks\n"
        "Use /help for instructions"
    )

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation to add a new task."""
    reply_keyboard = [['Day Task', 'Week Task']]
    
    await update.message.reply_text(
        "What type of task would you like to add?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Day or Week Task?'
        ),
    )
    
    return TASK_TYPE

async def task_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store task type and ask for description."""
    task_type = update.message.text
    context.user_data['task_type'] = task_type
    
    await update.message.reply_text(
        f"Please enter the task description for your {task_type}:",
        reply_markup=ReplyKeyboardRemove(),
    )
    
    return DAY_DESC if task_type == 'Day Task' else WEEK_DESC

async def day_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store day task description and ask for time."""
    description = update.message.text
    context.user_data['description'] = description
    
    await update.message.reply_text(
        "Please enter the time to complete (HH:MM, 24-hour format):"
    )
    
    return DAY_TIME

async def week_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store week task description and ask for day."""
    description = update.message.text
    context.user_data['description'] = description
    
    reply_keyboard = [['Mon', 'Tue', 'Wed'], ['Thu', 'Fri', 'Sat'], ['Sun']]
    
    await update.message.reply_text(
        "Please choose the day to complete:",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True
        ),
    )
    
    return WEEK_DAY

async def save_day_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save day task with time and end conversation."""
    time_str = update.message.text
    
    try:
        # Validate time format
        time_obj = datetime.datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        await update.message.reply_text("Invalid time format. Please use HH:MM (24-hour format).")
        return DAY_TIME
    
    # Create task dictionary
    task = {
        'type': 'day',
        'description': context.user_data['description'],
        'time': time_str,
        'created': datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M"),
        'completed': False
    }
    
    # Initialize user's task list if not exists
    if 'tasks' not in context.user_data:
        context.user_data['tasks'] = []
    
    # Add task and confirm
    context.user_data['tasks'].append(task)
    await update.message.reply_text(
        f"✅ Task added: \"{task['description']}\" due today at {time_str}"
    )
    
    # Schedule reminder
    await schedule_reminder(update, context, task)
    
    return ConversationHandler.END

async def save_week_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save week task with day and end conversation."""
    day = update.message.text
    
    # Create task dictionary
    task = {
        'type': 'week',
        'description': context.user_data['description'],
        'day': day,
        'created': datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M"),
        'completed': False
    }
    
    # Initialize user's task list if not exists
    if 'tasks' not in context.user_data:
        context.user_data['tasks'] = []
    
    # Add task and confirm
    context.user_data['tasks'].append(task)
    await update.message.reply_text(
        f"✅ Task added: \"{task['description']}\" due by {day}"
    )
    
    # Schedule reminder
    await schedule_reminder(update, context, task)
    
    return ConversationHandler.END

async def schedule_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE, task: dict):
    """Schedule reminders for the task."""
    chat_id = update.message.chat_id
    
    if task['type'] == 'day':
        now = datetime.datetime.now(TIMEZONE)
        task_time = datetime.datetime.strptime(task['time'], "%H:%M").time()
        task_datetime = datetime.datetime.combine(now.date(), task_time)
        task_datetime = TIMEZONE.localize(task_datetime)
        
        # If task time hasn't passed, schedule reminder 30 min before
        if task_datetime > now:
            reminder_datetime = task_datetime - datetime.timedelta(minutes=30)
            if reminder_datetime > now:
                # Schedule 30-min before reminder
                context.job_queue.run_once(
                    send_reminder,
                    when=reminder_datetime,
                    data=(chat_id, task['description'], f"in 30 minutes at {task['time']}"),
                    name=f"reminder_{chat_id}_{task['description']}_30min"
                )
                await update.message.reply_text(f"⏰ Reminder set for {reminder_datetime.strftime('%H:%M')}")
            else:
                # Send immediate reminder if less than 30 min left
                await update.message.reply_text(f"⚠️ Task due soon at {task['time']}!")
            
            # Always schedule reminder at actual task time
            context.job_queue.run_once(
                send_reminder,
                when=task_datetime,
                data=(chat_id, task['description'], f"NOW! Time: {task['time']}"),
                name=f"reminder_{chat_id}_{task['description']}_now"
            )
        else:
            await update.message.reply_text(f"⚠️ Task time {task['time']} has already passed today")
    else:  # week task
        days_map = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6}
        day_num = days_map[task['day']]
        
        now = datetime.datetime.now(TIMEZONE)
        days_until = (day_num - now.weekday()) % 7
        if days_until == 0 and now.hour >= 10:  # If it's the same day but past 10 AM
            days_until = 7
        reminder_date = now.date() + datetime.timedelta(days=days_until)
        reminder_datetime = TIMEZONE.localize(datetime.datetime.combine(reminder_date, datetime.time(10, 0)))
        
        context.job_queue.run_once(
            send_reminder,
            when=reminder_datetime,
            data=(chat_id, task['description'], f"by {task['day']}"),
            name=f"reminder_{chat_id}_{task['description']}"
        )
        await update.message.reply_text(f"⏰ Reminder set for {task['day']} at 10:00 AM")

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send the reminder message with completion check."""
    job = context.job
    chat_id, description, due_info = job.data
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [InlineKeyboardButton("✅ Done", callback_data=f"done_{description}")],
        [InlineKeyboardButton("⏰ Reschedule", callback_data=f"reschedule_{description}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔔 Reminder: \"{description}\" is due {due_info}\n\nHave you completed this task?",
        reply_markup=reply_markup
    )

async def view_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the user their current tasks."""
    if 'tasks' not in context.user_data or not context.user_data['tasks']:
        await update.message.reply_text("You have no tasks yet!")
        return
    
    tasks = context.user_data['tasks']
    message = "Your current tasks:\n\n"
    
    for i, task in enumerate(tasks, 1):
        status = "✅" if task['completed'] else "⏳"
        if task['type'] == 'day':
            message += f"{i}. {status} {task['description']} (Today at {task['time']})\n"
        else:
            message += f"{i}. {status} {task['description']} (By {task['day']})\n"
    
    await update.message.reply_text(message)

async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a task by number."""
    if 'tasks' not in context.user_data or not context.user_data['tasks']:
        await update.message.reply_text("You have no tasks to delete!")
        return
    
    tasks = context.user_data['tasks']
    message = "Select task number to delete:\n\n"
    
    for i, task in enumerate(tasks, 1):
        if task['type'] == 'day':
            message += f"{i}. {task['description']} (Today at {task['time']})\n"
        else:
            message += f"{i}. {task['description']} (By {task['day']})\n"
    
    message += "\nSend the task number to delete it."
    await update.message.reply_text(message)

async def handle_delete_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle task deletion by number."""
    try:
        task_num = int(update.message.text)
        if 'tasks' in context.user_data and 1 <= task_num <= len(context.user_data['tasks']):
            deleted_task = context.user_data['tasks'].pop(task_num - 1)
            await update.message.reply_text(f"🗑️ Deleted: \"{deleted_task['description']}\"")
        else:
            await update.message.reply_text("Invalid task number!")
    except ValueError:
        pass  # Not a number, ignore

async def handle_greeting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle greetings and show menu."""
    reply_keyboard = [['Add Task', 'View Tasks'], ['Delete Task']]
    
    await update.message.reply_text(
        "Hi, I am your notify bot! 🤖\n\nWhat would you like to do?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True
        ),
    )

async def handle_thank_you(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle thank you messages."""
    await update.message.reply_text(
        "You're welcome! 😊 Have a great day!",
        reply_markup=ReplyKeyboardRemove()
    )

async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle menu button selections."""
    text = update.message.text
    
    if text == 'Add Task':
        return await add_task(update, context)
    elif text == 'View Tasks':
        await view_tasks(update, context)
    elif text == 'Delete Task':
        await delete_task(update, context)
    
    return ConversationHandler.END

async def handle_task_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle task completion and reschedule callbacks."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("done_"):
        task_desc = data[5:]  # Remove "done_" prefix
        await query.edit_message_text(f"✅ Great! Task \"{task_desc}\" marked as completed!")
    
    elif data.startswith("reschedule_"):
        task_desc = data[11:]  # Remove "reschedule_" prefix
        keyboard = [
            [InlineKeyboardButton("⏰ 30 minutes", callback_data=f"snooze_30_{task_desc}")],
            [InlineKeyboardButton("⏰ 1 hour", callback_data=f"snooze_60_{task_desc}")],
            [InlineKeyboardButton("⏰ 2 hours", callback_data=f"snooze_120_{task_desc}")],
            [InlineKeyboardButton("📅 Tomorrow", callback_data=f"snooze_1440_{task_desc}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"⏰ Reschedule \"{task_desc}\" for:",
            reply_markup=reply_markup
        )
    
    elif data.startswith("snooze_"):
        parts = data.split("_", 2)
        minutes = int(parts[1])
        task_desc = parts[2]
        
        # Schedule new reminder
        chat_id = query.message.chat_id
        reminder_time = datetime.datetime.now(TIMEZONE) + datetime.timedelta(minutes=minutes)
        
        context.job_queue.run_once(
            send_reminder,
            when=reminder_time,
            data=(chat_id, task_desc, f"rescheduled for {reminder_time.strftime('%H:%M')}"),
            name=f"reminder_{chat_id}_{task_desc}_rescheduled"
        )
        
        if minutes >= 1440:
            time_text = "tomorrow"
        elif minutes >= 60:
            time_text = f"{minutes//60} hour(s)"
        else:
            time_text = f"{minutes} minutes"
            
        await query.edit_message_text(
            f"⏰ Task \"{task_desc}\" rescheduled for {time_text}!\n"
            f"New reminder at: {reminder_time.strftime('%H:%M')}"
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current conversation."""
    await update.message.reply_text(
        'Task addition cancelled.', reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    logger.error('Update "%s" caused error "%s"', update, context.error)

def setup_daily_notification(application):
    """Setup daily notification at 10 AM."""
    # Schedule daily notification at 10 AM
    application.job_queue.run_daily(
        morning_notification,
        time=datetime.time(10, 0, 0, tzinfo=TIMEZONE),
        days=tuple(range(7)),
    )

async def morning_notification(context: ContextTypes.DEFAULT_TYPE):
    """Send morning notification to all users."""
    # In a real app, you'd iterate through all users in your database
    # For this example, we'll just log it
    logger.info("Morning notification sent")

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    persistence = PicklePersistence(filepath='todo_bot_persistence')
    bot_token = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
    application = Application.builder().token(bot_token).persistence(persistence).build()

    # Add conversation handler with the states
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('addtask', add_task),
            MessageHandler(filters.Regex('^Add Task$'), handle_menu_selection)
        ],
        states={
            TASK_TYPE: [MessageHandler(filters.Regex('^(Day Task|Week Task)$'), task_type)],
            DAY_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, day_description)],
            DAY_TIME: [MessageHandler(filters.Regex('^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'), save_day_task)],
            WEEK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, week_description)],
            WEEK_DAY: [MessageHandler(filters.Regex('^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)$'), save_week_task)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('viewtasks', view_tasks))
    application.add_handler(CommandHandler('deletetask', delete_task))
    
    # Handle greetings
    application.add_handler(MessageHandler(filters.Regex(r'(?i)^(hi|hello|hey)$'), handle_greeting))
    
    # Handle thank you
    application.add_handler(MessageHandler(filters.Regex(r'(?i)^(thank you|thanks|thx)$'), handle_thank_you))
    
    # Handle menu selections (only View Tasks and Delete Task, Add Task is handled by conversation)
    application.add_handler(MessageHandler(filters.Regex('^(View Tasks|Delete Task)$'), handle_menu_selection))
    
    # Handle task deletion numbers
    application.add_handler(MessageHandler(filters.Regex(r'^\d+$'), handle_delete_number))
    
    # Handle callback queries for task completion/rescheduling
    application.add_handler(CallbackQueryHandler(handle_task_callback))
    
    application.add_error_handler(error_handler)

    # Setup daily notification on bot startup
    setup_daily_notification(application)

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()