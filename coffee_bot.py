import asyncio  # Для запуска асинхронных функций
from datetime import datetime  # Для отметок времени в логах
from pathlib import Path  # Для работы с файловой системой
from typing import List, Union, Optional  # Аннотации типов
import random

import aiohttp
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters.command import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from conf import coffee_bot_token

API_TOKEN: str = coffee_bot_token
LOG_DIR: Path = Path("coffee_logs")
LOG_DIR.mkdir(exist_ok=True)

TASTY_URL: str = "https://shop.tastycoffee.ru/coffee?page=2"
API_COFFEE_LIST_URL: str = "https://api.sampleapis.com/coffee/hot"
BASE_URL: str = "https://shop.tastycoffee.ru"

MAIN_KEYBOARD: ReplyKeyboardMarkup = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📦 Последние сорта"),
            KeyboardButton(text="🎲 Случайный кофе"),
        ],
        [
            KeyboardButton(text="📋 Список сортов"),
            KeyboardButton(text="🧪 Подбор по вкусам"),
        ],
        [
            KeyboardButton(text="☕ Советы"),
            KeyboardButton(text="ℹ️ О кофе"),
        ],
    ],
    resize_keyboard=True
)

BREWING_TIPS: List[str] = [
    "1. Используйте свежемолотый кофе.",
    "2. Температура воды — 92‑96°C.",
    "3. Не заливайте кипятком — горечь!",
    "4. Пропорция: 60 г кофе на литр воды.",
    "5. Экспериментируйте с помолом.",
]

ABOUT_COFFEE_TEXT: str = (
    "Кофе — напиток из обжаренных зёрен. Повышает бодрость, улучшает настроение, популярен во всём мире."
)

class FlavorSearch(StatesGroup):
    waiting_for_flavors = State()

def log_message(message: Message) -> None:
    user = message.from_user
    log_file = LOG_DIR / f"user_{user.id}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} | {user.id} | {message.text}\n")

async def send_and_log(message: Message, content: Union[str, List[str]]) -> None:
    user = message.from_user
    log_file = LOG_DIR / f"user_{user.id}.log"
    def _log(entry: str):
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} | Bot: {entry}\n")
    if isinstance(content, list):
        for text in content:
            await message.answer(text, parse_mode=ParseMode.HTML)
            _log(text)
    else:
        await message.answer(content, parse_mode=ParseMode.HTML)
        _log(content)

async def fetch_html(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    try:
        async with session.get(url, timeout=10) as resp:
            if resp.status == 200:
                return await resp.text()
    except:
        return None

async def parse_coffee_page(url: str = TASTY_URL, limit: int = 5) -> List[str]:
    async with aiohttp.ClientSession() as session:
        html = await fetch_html(session, url)
        if not html:
            return ["❌ Не удалось загрузить страницу."]
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("div.product-item")
    results = []
    for idx, item in enumerate(items[:limit]):
        title_tag = item.select_one("div.tc-tile__title a")
        name = title_tag.get_text(strip=True) if title_tag else "—"
        rel_link = title_tag.get("href", "") if title_tag else ""
        full_link = BASE_URL + rel_link
        price_tag = item.select_one(".tc-tile__price span")
        price_text = price_tag.get_text(strip=True) if price_tag else "—"
        results.append(f"☕ <b>{name}</b>\n💰 {price_text}\n🔗 <a href=\"{full_link}\">Ссылка</a>")
    return results or ["ℹ️ Нет данных."]

async def translate_text(text: str, dest: str = "ru") -> str:
    import urllib.parse
    try:
        encoded = urllib.parse.quote(text)
        url = (
            f"https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=auto&tl={dest}&dt=t&q={encoded}"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return text
                arr = await resp.json()
                if isinstance(arr, list) and arr and isinstance(arr[0], list):
                    return arr[0][0][0]
                else:
                    return text
    except:
        return text

async def get_coffee_list() -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_COFFEE_LIST_URL) as resp:
                data = await resp.json()
    except Exception as e:
        return f"Ошибка: {e}"
    lines = ["Популярные сорта:"]
    for item in data[:10]:
        en = item.get("title", "—")
        ru = await translate_text(en, dest="ru")
        lines.append(f"• {ru}")
    return "\n".join(lines)

async def get_coffee_random() -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_COFFEE_LIST_URL) as resp:
                data = await resp.json()
    except:
        return "Ошибка API"
    item = random.choice(data)
    title = item.get("title", "—")
    desc = item.get("description", "—")
    title_ru = await translate_text(title, dest="ru")
    desc_ru = await translate_text(desc, dest="ru")
    return f"🎲 <b>{title_ru}</b>\n\n{desc_ru}"

async def get_all_flavor_notes() -> List[str]:
    async with aiohttp.ClientSession() as session:
        html = await fetch_html(session, TASTY_URL)
        if not html:
            return []
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("div.product-item")
    notes_set = set()
    for item in items:
        desc_container = item.select_one("div.tc-tile__description")
        if not desc_container:
            continue
        description_p = desc_container.find("p")
        if not description_p:
            continue
        for span in description_p.select("span.descriptor-badge"):
            notes_set.add(span.get_text(strip=True).lower())
    return sorted(notes_set)

async def find_coffee_by_flavors(flavors: List[str]) -> List[str]:
    async with aiohttp.ClientSession() as session:
        html = await fetch_html(session, TASTY_URL)
        if not html:
            return ["Ошибка загрузки."]
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("div.product-item")
    results = []
    for item in items:
        title_tag = item.select_one("div.tc-tile__title a")
        name_en = title_tag.get_text(strip=True) if title_tag else "—"
        link = BASE_URL + (title_tag.get("href", "") if title_tag else "")
        name_ru = await translate_text(name_en)
        desc_container = item.select_one("div.tc-tile__description")
        if not desc_container:
            continue
        description_p = desc_container.find("p")
        if not description_p:
            continue
        notes = [s.get_text(strip=True).lower() for s in description_p.select("span.descriptor-badge")]
        if all(f in notes for f in flavors):
            results.append(f"☕ <b>{name_ru}</b>\nВкусы: {', '.join(notes)}\n🔗 <a href=\"{link}\">Ссылка</a>")
    return results or ["Совпадений не найдено."]

bot = Bot(token=API_TOKEN)
_dp = Dispatcher()

@_dp.message(Command("start"))
async def cmd_start(message: Message):
    log_message(message)
    text = "Привет! Я бот про кофе ☕\nВыбирайте действие через кнопки ниже."
    await message.answer(text, reply_markup=MAIN_KEYBOARD)

@_dp.message(lambda m: m.text == "📦 Последние сорта")
async def latest_coffee(message: Message):
    log_message(message)
    await send_and_log(message, await parse_coffee_page())

@_dp.message(lambda m: m.text == "🎲 Случайный кофе")
async def random_coffee(message: Message):
    log_message(message)
    await send_and_log(message, await get_coffee_random())

@_dp.message(lambda m: m.text == "📋 Список сортов")
async def coffee_list(message: Message):
    log_message(message)
    await send_and_log(message, await get_coffee_list())

@_dp.message(lambda m: m.text == "☕ Советы")
async def brewing_tips(message: Message):
    log_message(message)
    await send_and_log(message, "\n".join(BREWING_TIPS))

@_dp.message(lambda m: m.text == "ℹ️ О кофе")
async def about_coffee(message: Message):
    log_message(message)
    await send_and_log(message, ABOUT_COFFEE_TEXT)

@_dp.message(lambda m: m.text == "🧪 Подбор по вкусам")
async def select_flavors(message: Message, state: FSMContext):
    log_message(message)
    notes = await get_all_flavor_notes()
    if not notes:
        await message.answer("Не удалось получить список вкусов 😔")
        return
    await message.answer("Доступные вкусы:\n" + ", ".join(notes))
    await message.answer("Введите нужные вкусы через запятую:")
    await state.set_state(FlavorSearch.waiting_for_flavors)

@_dp.message(FlavorSearch.waiting_for_flavors)
async def process_flavors(message: Message, state: FSMContext):
    log_message(message)
    flavors = [f.strip().lower() for f in message.text.split(",") if f.strip()]
    if not flavors:
        await message.answer("Не распознаны вкусы. Повторите ввод:")
        return
    await send_and_log(message, await find_coffee_by_flavors(flavors))
    await state.clear()

if __name__ == "__main__":
    print("Кофе-бот запущен...")
    asyncio.run(_dp.start_polling(bot))
