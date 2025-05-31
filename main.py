import logging
from datetime import datetime
from pathlib import Path

import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardMarkup, KeyboardButton

from bs4 import BeautifulSoup
from conf import token_tg

# === Настройка токена (замените на свой) ===
API_TOKEN = token_tg

# === Логирование ===

# Папка для логов
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

def log_message(message: Message):
    user = message.from_user
    log_file = log_dir / f"user_{user.id}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        log_entry = (f"{datetime.now().isoformat()} | "
                     f"User {user.id} ({user.full_name} | @{user.username}) | "
                     f"Message: {message.text}\n")
        f.write(log_entry)

# === Инициализация бота и диспетчера ===
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# === Скрипт скраппинга новостей с darkreading.com ===
def scrape_securitylab_news():
    url = "https://www.securitylab.ru/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/"
    }

    try:
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        articles = soup.select("div.article-card")[:5]

        news_items = []
        base_url = "https://www.securitylab.ru"

        for article in articles:
            title_tag = article.select_one("h4.article-card-title") or article.select_one("h2.article-card-title")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)

            link_tag = title_tag.find_parent("a")
            if not link_tag:
                continue
            href = link_tag.get("href")
            full_link = href if href.startswith("http") else base_url + href

            desc_tag = article.select_one("p")
            description = desc_tag.get_text(strip=True) if desc_tag else ""

            time_tag = article.select_one("time")
            date_str = time_tag.get_text(strip=True) if time_tag else ""

            item_text = f"• {title}\n{full_link}"
            if description:
                item_text += f"\n{description}"
            if date_str:
                item_text += f"\n🕒 {date_str}"

            news_items.append(item_text)

        if not news_items:
            return "Новости сейчас недоступны."

        return "\n\n".join(news_items)

    except Exception as e:
        return f"Ошибка при получении новостей: {e}"


# === API для CVSS ===
import requests

def get_cvss_score(cvss_vector: str):
    """
    Запрос к API FIRST.org для получения оценки CVSS по вектору.

    cvss_vector — строка в формате CVSS v3, например:
    "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"

    Возвращает строку с результатом или ошибку.
    """
    url = "https://api.first.org/data/cvss/v3"
    params = {
        "vector": cvss_vector
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        if "data" in data:
            scored = data["data"]
            # Пример создания удобного вывода
            base_score = scored.get("baseScore", "N/A")
            severity = scored.get("baseSeverity", "N/A")
            vector = scored.get("vectorString", "")
            return f"CVSS v3 Score: {base_score} ({severity})\nВектор: {vector}"
        else:
            return "Данные CVSS не получены."
    except Exception as e:
        return f"Ошибка при запросе CVSS API: {e}"



# функция для отправки и логирования сообщений бота
async def send_and_log(message: Message, text: str):
    await message.answer(text)
    user = message.from_user
    log_file = log_dir / f"user_{user.id}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        log_entry = f"{datetime.now().isoformat()} | Bot sent: {text}\n"
        f.write(log_entry)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    log_message(message)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/latest_news"), KeyboardButton(text="/cvss_score")],
            [KeyboardButton(text="/tips")],
        ],
        resize_keyboard=True
    )
    await send_and_log(
        message,
        "Привет! Я бот по информационной безопасности.\n"
        "Вот мои команды:\n"
        "/latest_news — последние новости по инфобезу\n"
        "/cvss_score — краткая информация по CVSS\n"
        "/tips — советы по защите данных\n"
    )

@dp.message(Command("latest_news"))
async def cmd_latest_news(message: Message):
    log_message(message)
    await send_and_log(message, "Пожалуйста, подождите, получаю последние новости...")
    news = scrape_securitylab_news()
    await send_and_log(message, news)

@dp.message(Command("cvss_score"))
async def cmd_cvss_score(message: Message):
    log_message(message)
    await send_and_log(message, "Получаю информацию о CVSS...")
    info = get_cvss_score()
    await send_and_log(message, info)

@dp.message(Command("tips"))
async def cmd_tips(message: Message):
    log_message(message)
    tips_list = [
        "1. Используйте сложные пароли и двухфакторную аутентификацию.",
        "2. Регулярно обновляйте софт и операционную систему.",
        "3. Не открывайте подозрительные ссылки и вложения.",
        "4. Используйте антивирус и файрволл.",
        "5. Шифруйте важные данные и резервные копии.",
    ]
    await send_and_log(message, "\n".join(tips_list))

# Запуск бота
if __name__ == "__main__":
    import asyncio
    print("Бот запущен...")
    asyncio.run(dp.start_polling(bot))
