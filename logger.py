import os
from datetime import datetime

# Создаем папку для логов, если её нет
os.makedirs("user_logs", exist_ok=True)

async def log_interaction(user_id: int, user_message: str, bot_response: str = None,
                          media_type: str = None, media_url: str = None):
    log_file = f"user_logs/{user_id}.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}]\nUser: {user_message}\n"
    if bot_response:
        log_entry += f"Bot: {bot_response}\n"
    if media_type:
        log_entry += f"Media: {media_type} ({media_url})\n"
    log_entry += "="*50 + "\n"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)