import asyncio
from datetime import datetime
from pathlib import Path

import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardMarkup, KeyboardButton
from bs4 import BeautifulSoup
from conf import coffee_bot_token
# === Настройка токена ===
API_TOKEN = coffee_bot_token

# === Папка для логов ===
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

async def send_and_log(message: Message, text: str):
    await message.answer(text)
    user = message.from_user
    log_file = log_dir / f"user_{user.id}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        log_entry = f"{datetime.now().isoformat()} | Bot sent: {text}\n"
        f.write(log_entry)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# === Скраппинг tastycoffee.ru/coffee для последних 5 сортов ===
def scrape_tastycoffee_latest():
    url = "https://shop.tastycoffee.ru/coffee"
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/114.0.0.0 Safari/537.36")
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Структура сайта: блоки товаров с классом product-item или аналог
        products = soup.select("div.product-item")[:5]
        if not products:
            return "Не удалось найти товары на сайте."

        items = []
        base_url = "https://shop.tastycoffee.ru"
        for p in products:
            # Название
            name_tag = p.select_one("a.product-title") or p.select_one("div.product-title a")
            name = name_tag.get_text(strip=True) if name_tag else "Нет названия"
            href = name_tag.get("href") if name_tag else ""
            full_link = href if href.startswith("http") else base_url + href

            # Цена
            price_tag = p.select_one("span.price") or p.select_one("div.price")
            price = price_tag.get_text(strip=True) if price_tag else "Цена не указана"

            item_text = f"• {name}\n{full_link}\nЦена: {price}"
            items.append(item_text)

        return "\n\n".join(items)

    except Exception as e:
        return f"Ошибка при получении кофейных продуктов: {e}"

# === API sampleapis.com для кофе ===
API_COFFEE_LIST_URL = "https://api.sampleapis.com/coffee/hot"  # Горячий кофе

def get_coffee_list():
    try:
        r = requests.get(API_COFFEE_LIST_URL, timeout=10)
        r.raise_for_status()
        data = r.json()
        # Выведем первые 10 названий
        names = [item["title"] for item in data[:10]]
        return "Популярные сорта кофе:\n" + "\n".join(f"• {n}" for n in names)
    except Exception as e:
        return f"Ошибка при получении списка кофе: {e}"

def get_coffee_random():
    try:
        r = requests.get(API_COFFEE_LIST_URL, timeout=10)
        r.raise_for_status()
        data = r.json()
        import random
        item = random.choice(data)
        desc = item.get("description", "Описание отсутствует")
        return f"Случайный кофе:\n\nНазвание: {item['title']}\n\nОписание:\n{desc}"
    except Exception as e:
        return f"Ошибка при получении случайного кофе: {e}"

# Статичные советы по приготовлению кофе
brewing_tips = [
    "1. Используйте свежемолотый кофе для лучшего вкуса.",
    "2. Соблюдайте правильную температуру воды — 92-96°C.",
    "3. Не заливайте кофе кипятком, чтобы избежать горечи.",
    "4. Используйте правильную пропорцию: около 60 грамм кофе на литр воды.",
    "5. Экспериментируйте с разными помолами для разных способов приготовления."
]

# Статичная информация про кофе
about_coffee_text = (
    "Кофе — это напиток, приготовленный из обжаренных зёрен кофейного дерева.\n"
    "Существует множество сортов и способов его приготовления. Кофе повышает бодрость, "
    "улучшает настроение и является одним из самых популярных напитков в мире."
)

# === Хендлеры команд ===

@dp.message(Command("start"))
async def cmd_start(message: Message):
    log_message(message)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/latest_coffee"), KeyboardButton(text="/coffee_random"), KeyboardButton(text="/coffee_list")],
            [KeyboardButton(text="/brewing_tips"), KeyboardButton(text="/about_coffee")],
        ],
        resize_keyboard=True
    )
    await send_and_log(
        message,
        "Привет! Я бот про кофе ☕\n"
        "Вот мои команды:\n"
        "/latest_coffee — последние 5 сортов кофе с tastycoffee.ru\n"
        "/coffee_random — случайный кофе из API\n"
        "/coffee_list — список популярных сортов кофе из API\n"
        "/brewing_tips — советы по приготовлению кофе\n"
        "/about_coffee — кратко о кофе\n"
    )

@dp.message(Command("latest_coffee"))
async def cmd_latest_coffee(message: Message):
    log_message(message)
    await send_and_log(message, "Подождите, получаю последние сорта кофе...")
    news = scrape_tastycoffee_latest()
    await send_and_log(message, news)

@dp.message(Command("coffee_random"))
async def cmd_coffee_random(message: Message):
    log_message(message)
    await send_and_log(message, "Ищу случайный кофе...")
    coffee = get_coffee_random()
    await send_and_log(message, coffee)

@dp.message(Command("coffee_list"))
async def cmd_coffee_list(message: Message):
    log_message(message)
    await send_and_log(message, "Список популярных сортов кофе:")
    coffee_list = get_coffee_list()
    await send_and_log(message, coffee_list)

@dp.message(Command("brewing_tips"))
async def cmd_brewing_tips(message: Message):
    log_message(message)
    await send_and_log(message, "\n".join(brewing_tips))

@dp.message(Command("about_coffee"))
async def cmd_about_coffee(message: Message):
    log_message(message)
    await send_and_log(message, about_coffee_text)

if __name__ == "__main__":
    print("Кофейный бот запущен...")
    asyncio.run(dp.start_polling(bot))
