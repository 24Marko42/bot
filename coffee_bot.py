import asyncio  # Для запуска асинхронных функций
from datetime import datetime  # Для отметок времени в логах
from pathlib import Path  # Для работы с файловой системой
from typing import List, Union, Optional  # Аннотации типов

import aiohttp  # Асинхронные HTTP-запросы
from bs4 import BeautifulSoup  # Для парсинга HTML
from aiogram import Bot, Dispatcher, types  # Основные классы Aiogram
from aiogram.filters.command import Command  # Фильтр для команд
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode  # Для указания HTML-формата при отправке
import urllib.parse

from conf import coffee_bot_token  # Предположим, что токен лежит здесь

# === КОНСТАНТЫ ===
API_TOKEN: str = coffee_bot_token  # Токен Telegram-бота
LOG_DIR: Path = Path("coffee_logs")  # Папка для логов
LOG_DIR.mkdir(exist_ok=True)  # Создаём папку, если её нет

TASTY_URL: str = "https://shop.tastycoffee.ru/coffee?page=2"  # Страница с товарами
API_COFFEE_LIST_URL: str = "https://api.sampleapis.com/coffee/hot"  # API списка кофе
BASE_URL: str = "https://shop.tastycoffee.ru"  # Для полного URL товаров

# Клавиатура, показываемая при /start
MAIN_KEYBOARD: ReplyKeyboardMarkup = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="/latest_coffee"),
            KeyboardButton(text="/coffee_random"),
            KeyboardButton(text="/coffee_list"),
        ],
        [
            KeyboardButton(text="/brewing_tips"),
            KeyboardButton(text="/about_coffee"),
        ],
    ],
    resize_keyboard=True
)

# Советы по приготовлению кофе
BREWING_TIPS: List[str] = [
    "1. Используйте свежемолотый кофе для лучшего вкуса.",
    "2. Соблюдайте правильную температуру воды — 92‑96°C.",
    "3. Не заливайте кофе кипятком, чтобы избежать горечи.",
    "4. Используйте правильную пропорцию: около 60 г кофе на литр воды.",
    "5. Экспериментируйте с разными помолами для разных способов приготовления.",
]

# Информация про кофе
ABOUT_COFFEE_TEXT: str = (
    "Кофе — это напиток, приготовленный из обжаренных зёрен кофейного дерева.\n"
    "Существует множество сортов и способов его приготовления. Кофе повышает бодрость, "
    "улучшает настроение и является одним из самых популярных напитков в мире."
)

# === ФУНКЦИЯ-ПЕРЕВОДЧИК через LibreTranslate ===
async def translate_text(text: str, dest: str = "ru") -> str:
    """
    Переводит текст с помощью "неофициального" Google Translate API:
      GET https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=<dest>&dt=t&q=<вроде бы URL‑encoded текст>
    Если перевод не удаётся, возвращает исходный текст.
    """
    try:
        # URL‑encode текста
        encoded = urllib.parse.quote(text)
        url = (
            f"https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=auto&tl={dest}&dt=t&q={encoded}"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return text
                # Ответ—JSON, например: [[[ "Переведённый текст", ... ]], ...]
                arr = await resp.json()
                # Первым элементом массива arr[0][0][0] лежит переведённая строка
                if isinstance(arr, list) and arr and isinstance(arr[0], list):
                    translated = arr[0][0][0]
                    return translated
                else:
                    return text
    except Exception:
        return text

# === ЛОГИРОВАНИЕ ===
def log_message(message: Message) -> None:
    """
    Логируем входящее сообщение в файл coffee_logs/user_<id>.log.
    """
    user = message.from_user
    log_file = LOG_DIR / f"user_{user.id}.log"
    text = message.text or ""
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(
            f"{datetime.now().isoformat()} | "
            f"User {user.id} ({user.full_name} | @{user.username}) | "
            f"Message: {text}\n"
        )

async def send_and_log(message: Message, content: Union[str, List[str]]) -> None:
    """
    Отправляем одной строкой или списком строк и логируем.
    Если content — список, отправляем каждый элемент отдельно.
    """
    user = message.from_user
    log_file = LOG_DIR / f"user_{user.id}.log"

    def _write_log(entry: str) -> None:
        with open(log_file, "a", encoding="utf-8") as f_log:
            f_log.write(f"{datetime.now().isoformat()} | Bot sent: {entry}\n")

    if isinstance(content, list):
        for text in content:
            await message.answer(text, parse_mode=ParseMode.HTML)
            _write_log(text)
    else:
        await message.answer(content, parse_mode=ParseMode.HTML)
        _write_log(content)

# === АСИНХРОННЫЕ HTTP‑ФУНКЦИИ ===
async def fetch_html(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    """
    Асинхронный GET-запрос, возвращает HTML либо None.
    """
    try:
        async with session.get(url, timeout=10) as resp:
            if resp.status == 200:
                return await resp.text()
            else:
                return None
    except asyncio.TimeoutError:
        return None
    except aiohttp.ClientError:
        return None

async def parse_coffee_page(url: str = TASTY_URL, limit: int = 5) -> List[str]:
    """
    Парсим страницу tastycoffee.ru/coffee?page=2, извлекаем первые `limit` товаров:
      • название (английское) → переводим
      • цена
      • ссылка
      • описание (английское) → переводим
      • ноты вкуса (обычно уже на русском)
    Возвращаем список форматированных HTML-строк. Если не удалось, возвращаем строку-ошибку.
    """
    async with aiohttp.ClientSession() as session:
        html = await fetch_html(session, url)
        if not html:
            return ["❌ Ошибка при запросе к tastycoffee.ru"]

    soup = BeautifulSoup(html, "html.parser")
    # Селектор под текущую верстку: карточки имеют класс "product-item"
    items = soup.select("div.product-item")
    results: List[str] = []

    for idx, item in enumerate(items):
        if idx >= limit:
            break  # Берём не более limit товаров

        # 1) Название и ссылка в <div.tc-tile__title a>
        title_tag = item.select_one("div.tc-tile__title a")
        if not title_tag:
            continue
        name_en = title_tag.get_text(strip=True)
        # Асинхронно переводим название
        name_ru = await translate_text(name_en, dest="ru")
        rel_link = title_tag.get("href", "").strip()
        full_link = BASE_URL + rel_link

        # 2) Цена в <div class="product_price__value">
        price_tag = item.select_one(".product_price__value")
        price_text = price_tag.get_text(strip=True) if price_tag else "—"

        # 3) Описание внутри <p class="text-[14px] ...">
        desc_container = item.select_one("div.tc-tile__description")
        if desc_container:
            description_p = desc_container.find("p", class_="text-[14px]")
            if description_p:
                description_en = description_p.get_text(separator=" ", strip=True)
                # Асинхронно переводим описание
                description_ru = await translate_text(description_en, dest="ru")
            else:
                description_ru = ""
        else:
            description_ru = ""

        # 4) Ноты вкуса (<span class="descriptor-badge">)
        notes_list = []
        if desc_container and description_p:
            for span in description_p.find_all("span", class_="descriptor-badge"):
                notes_list.append(span.get_text(strip=True))
        notes_text = ", ".join(notes_list) if notes_list else "—"

        results.append(
            f"☕ <b>{name_ru}</b>\n"  # Название (уже на русском)
            f"💰 {price_text}\n"      # Цена
            f"🔗 <a href=\"{full_link}\">Ссылка</a>\n\n"  # Ссылка
            f"ℹ️ <i>{description_ru}</i>\n\n"  # Описание (на русском)
            f"Ноты вкуса: {notes_text}"       # Ноты вкуса
        )

    if not results:
        return ["ℹ️ Не удалось найти товары на странице."]
    return results

async def get_coffee_list() -> str:
    """
    Асинхронно получает первые 10 названий сортов кофе и переводит их на русский.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_COFFEE_LIST_URL, timeout=10) as resp:
                resp.raise_for_status()
                data = await resp.json()
    except Exception as e:
        return f"❌ Ошибка при получении списка кофе: {e}"

    result_lines = ["Популярные сорта кофе из API:"]
    for item in data[:10]:
        title_en = item.get("title", "—")
        try:
            title_ru = await translate_text(title_en, dest="ru")
        except Exception:
            title_ru = title_en
        result_lines.append(f"• {title_ru}")
    
    return "\n".join(result_lines)

async def get_coffee_random() -> str:
    """
    Асинхронно берёт весь список кофе и возвращает один случайный элемент.
    Переводит название и описание на русский.
    """
    import random

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_COFFEE_LIST_URL, timeout=10) as resp:
                resp.raise_for_status()
                data = await resp.json()
    except Exception as e:
        return f"❌ Ошибка при получении данных для случайного кофе: {e}"

    if not isinstance(data, list) or not data:
        return "ℹ️ Данные от API пришли в неожиданном формате."

    item = random.choice(data)
    title_en = item.get("title", "—")
    description_en = item.get("description", "Описание отсутствует")

    try:
        title_ru = await translate_text(title_en, dest="ru")
        description_ru = await translate_text(description_en, dest="ru")
    except Exception:
        title_ru = title_en
        description_ru = description_en

    return (
        f"🎲 <b>Случайный кофе</b>:\n\n"
        f"Название: <b>{title_ru}</b>\n\n"
        f"Описание:\n{description_ru}"
    )

# === СОЗДАЁМ БОТА И ДИСПЕТЧЕР ===
bot: Bot = Bot(token=API_TOKEN)
dp: Dispatcher = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """
    Команда /start: логируем, отправляем приветствие и показываем MAIN_KEYBOARD.
    """
    log_message(message)
    welcome_text = (
        "Привет! Я бот про кофе ☕\n\n"
        "Вот мои команды:\n"
        "/latest_coffee — последние 5 сортов кофе с tastycoffee.ru (с переводом)\n"
        "/coffee_random — случайный кофе из API (с переводом)\n"
        "/coffee_list — список популярных сортов кофе из API (с переводом)\n"
        "/brewing_tips — советы по приготовлению кофе\n"
        "/about_coffee — кратко о кофе"
    )
    await message.answer(welcome_text, reply_markup=MAIN_KEYBOARD)

@dp.message(Command("latest_coffee"))
async def cmd_latest_coffee(message: Message) -> None:
    """
    Команда /latest_coffee: парсим и шлём первые 5 товаров (названия и описания переведены).
    """
    log_message(message)
    await send_and_log(message, "🔍 Получаем последние 5 сортов кофе…")
    products = await parse_coffee_page()
    await send_and_log(message, products)

@dp.message(Command("coffee_random"))
async def cmd_coffee_random(message: Message) -> None:
    """
    Команда /coffee_random: шлём случайный кофе из API (переведен).
    """
    log_message(message)
    await send_and_log(message, "🍀 Ищу случайный кофе в API…")
    random_info = await get_coffee_random()
    await send_and_log(message, random_info)

@dp.message(Command("coffee_list"))
async def cmd_coffee_list(message: Message) -> None:
    """
    Команда /coffee_list: шлём список первых 10 сортов из API (переведено).
    """
    log_message(message)
    await send_and_log(message, "📋 Получаю список популярных сортов кофе…")
    coffee_list_text = await get_coffee_list()
    await send_and_log(message, coffee_list_text)

@dp.message(Command("brewing_tips"))
async def cmd_brewing_tips(message: Message) -> None:
    """
    Команда /brewing_tips: шлём советы по приготовлению кофе.
    """
    log_message(message)
    tips_text = "\n".join(BREWING_TIPS)
    await send_and_log(message, tips_text)

@dp.message(Command("about_coffee"))
async def cmd_about_coffee(message: Message) -> None:
    """
    Команда /about_coffee: шлём информацию о кофе.
    """
    log_message(message)
    await send_and_log(message, ABOUT_COFFEE_TEXT)

# === ТОЧКА ВХОДА ===
if __name__ == "__main__":
    print("☕ Кофейный бот запущен…")
    asyncio.run(dp.start_polling(bot))
