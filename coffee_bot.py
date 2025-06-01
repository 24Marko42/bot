import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Union, Optional

import aiohttp
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode

from conf import coffee_bot_token  # Предполагаем, что здесь лежит токен

# === Константы ===
API_TOKEN: str = coffee_bot_token
LOG_DIR: Path = Path("coffee_logs")
LOG_DIR.mkdir(exist_ok=True)

TASTY_URL: str = "https://shop.tastycoffee.ru/coffee?page=2"
API_COFFEE_LIST_URL: str = "https://api.sampleapis.com/coffee/hot"
BASE_URL: str = "https://shop.tastycoffee.ru"  # для сборки абсолютных ссылок

# Глобальная клавиатура (ReplyKeyboard)
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

# Статичные советы по приготовлению кофе
BREWING_TIPS: List[str] = [
    "1. Используйте свежемолотый кофе для лучшего вкуса.",
    "2. Соблюдайте правильную температуру воды — 92‑96°C.",
    "3. Не заливайте кофе кипятком, чтобы избежать горечи.",
    "4. Используйте правильную пропорцию: около 60 г кофе на литр воды.",
    "5. Экспериментируйте с разными помолами для разных способов приготовления.",
]

# Статичная информация про кофе
ABOUT_COFFEE_TEXT: str = (
    "Кофе — это напиток, приготовленный из обжаренных зёрен кофейного дерева.\n"
    "Существует множество сортов и способов его приготовления. Кофе повышает бодрость, "
    "улучшает настроение и является одним из самых популярных напитков в мире."
)

# === Логирование ===
def log_message(message: Message) -> None:
    """Логирует входящее сообщение пользователя в файл coffee_logs/user_<id>.log."""
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
    Отправляет текст (или список текстов) пользователю и логирует их.
    Если content — список, шлёт каждый элемент по отдельности.
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


# === Асинхронные HTTP‑функции ===
async def fetch_html(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    """
    Выполняет GET-запрос к указанному URL и возвращает текст страницы.
    В случае неуспеха возвращает None.
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
    Асинхронно парсит страницу tastycoffee.ru/coffee?page=2 и возвращает
    список HTML-строк с первыми `limit` сортами кофе. Для каждого товара собираются:
      - название
      - ссылка
      - полный текст описания (<p class="text-[14px] ...">…</p>)
      - список «нот вкуса» (<span class="descriptor-badge">…</span>)
    """
    async with aiohttp.ClientSession() as session:
        html = await fetch_html(session, url)
        if not html:
            return ["❌ Ошибка при запросе к tastycoffee.ru"]

    soup = BeautifulSoup(html, "html.parser")
    # Ищем все контейнеры товаров
    items = soup.select("div.product-item")
    results: List[str] = []

    for idx, item in enumerate(items):
        if idx >= limit:
            break

        # 1) Название и относительная ссылка
        title_tag = item.select_one("div.tc-tile__title a")
        if not title_tag:
            continue

        name = title_tag.get_text(strip=True)
        rel_link = title_tag.get("href", "").strip()
        full_link = BASE_URL + rel_link

        # 2) Блок описания (где лежит <p class="text-[14px] ...">)
        desc_container = item.select_one("div.tc-tile__description")
        if desc_container:
            # 2.1) сам тег <p>
            description_p = desc_container.find("p", class_="text-[14px]")
            if description_p:
                description = description_p.get_text(separator=" ", strip=True)
                # 2.2) ноты вкуса — все <span class="descriptor-badge">
                flavor_notes = [
                    span.get_text(strip=True)
                    for span in description_p.find_all("span", class_="descriptor-badge")
                ]
            else:
                description = ""
                flavor_notes = []
        else:
            description = ""
            flavor_notes = []

        # Формируем одну HTML-строку для отправки
        notes_text = ", ".join(flavor_notes) if flavor_notes else "—"
        result_str = (
            f"☕ <b>{name}</b>\n"
            f"🔗 <a href=\"{full_link}\">Перейти на товар</a>\n\n"
            f"ℹ️ <i>{description}</i>\n\n"
            f"Ноты вкуса: {notes_text}"
        )
        results.append(result_str)

    if not results:
        return ["ℹ️ Не удалось найти товары на странице."]
    return results


async def get_coffee_list() -> str:
    """
    Асинхронно получает первые 10 названий сортов кофе из sampleapis.com/coffee/hot.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_COFFEE_LIST_URL, timeout=10) as resp:
                resp.raise_for_status()
                data = await resp.json()
    except Exception as e:
        return f"❌ Ошибка при получении списка кофе: {e}"

    titles = [item.get("title", "—") for item in data[:10]]
    bullet_list = "\n".join(f"• {t}" for t in titles)
    return "Популярные сорта кофе из API:\n" + bullet_list


async def get_coffee_random() -> str:
    """
    Асинхронно берёт весь список кофе и возвращает один случайный элемент с описанием.
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
    title = item.get("title", "—")
    description = item.get("description", "Описание отсутствует")
    return (
        f"🎲 Случайный кофе:\n\n"
        f"Название: <b>{title}</b>\n\n"
        f"Описание:\n{description}"
    )


# === Создаём бот и диспетчер ===
bot: Bot = Bot(token=API_TOKEN)
dp: Dispatcher = Dispatcher()

# === Хэндлеры ===

@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    log_message(message)
    welcome_text = (
        "Привет! Я бот про кофе ☕\n\n"
        "Вот мои команды:\n"
        "/latest_coffee — последние 5 сортов кофе с tastycoffee.ru\n"
        "/coffee_random — случайный кофе из API\n"
        "/coffee_list — список популярных сортов кофе из API\n"
        "/brewing_tips — советы по приготовлению кофе\n"
        "/about_coffee — кратко о кофе"
    )
    await send_and_log(message, welcome_text)


@dp.message(Command("latest_coffee"))
async def cmd_latest_coffee(message: Message) -> None:
    log_message(message)
    await send_and_log(message, "🔍 Получаем последние 5 сортов кофе…")
    parsed = await parse_coffee_page()
    await send_and_log(message, parsed)


@dp.message(Command("coffee_random"))
async def cmd_coffee_random(message: Message) -> None:
    log_message(message)
    await send_and_log(message, "🍀 Ищу случайный кофе в API…")
    random_info = await get_coffee_random()
    await send_and_log(message, random_info)


@dp.message(Command("coffee_list"))
async def cmd_coffee_list(message: Message) -> None:
    log_message(message)
    await send_and_log(message, "📋 Получаю список популярных сортов кофе…")
    coffee_list_text = await get_coffee_list()
    await send_and_log(message, coffee_list_text)


@dp.message(Command("brewing_tips"))
async def cmd_brewing_tips(message: Message) -> None:
    log_message(message)
    tips_text = "\n".join(BREWING_TIPS)
    await send_and_log(message, tips_text)


@dp.message(Command("about_coffee"))
async def cmd_about_coffee(message: Message) -> None:
    log_message(message)
    await send_and_log(message, ABOUT_COFFEE_TEXT)


# === Точка входа ===
if __name__ == "__main__":
    print("☕ Кофейный бот запущен…")
    # Если вы хотите, чтобы клавиатура отображалась сразу после /start,
    # можно в cmd_start добавить: await message.answer("...", reply_markup=MAIN_KEYBOARD)
    asyncio.run(dp.start_polling(bot))
