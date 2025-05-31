from aiogram import Dispatcher, F
from aiogram.types import Message
from logger import log_interaction
from parser import get_coffee_products, get_coffee_quotes
import aiohttp

# Команда /start
async def start(message: Message):
    response = (
        "Привет! Я кофейный бот ☕\n\nДоступные команды:\n"
        "/coffee_list — популярные напитки (API)\n"
        "/coffee_image — фото кофе (API)\n"
        "/scrap_products — кофе из магазина (сайт)\n"
        "/coffee_quotes — цитаты о кофе (сайт)"
    )
    await message.answer(response)
    await log_interaction(message.from_user.id, message.text, response)

# API: список кофе
async def coffee_list(message: Message):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.sampleapis.com/coffee/hot") as resp:
                data = await resp.json()
        reply = "\n\n".join([f"☕ {x['title']}\n{x['description']}" for x in data[:5]])
    except Exception:
        reply = "❌ Ошибка при получении данных с API."
    await message.answer(reply)
    await log_interaction(message.from_user.id, message.text, reply)

# API: изображение кофе
async def coffee_image(message: Message):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://coffee.alexflipnote.dev/random.json") as resp:
                data = await resp.json()
        await message.answer_photo(data['file'])
        await log_interaction(message.from_user.id, message.text, "Фото кофе", "photo", data['file'])
    except Exception:
        error = "⚠️ Не удалось получить изображение."
        await message.answer(error)
        await log_interaction(message.from_user.id, message.text, error)

# Парсинг: товары кофе
async def scrap_products(message: Message):
    reply = await get_coffee_products()
    await message.answer(reply)
    await log_interaction(message.from_user.id, message.text, reply)

# Парсинг: цитаты о кофе
async def coffee_quotes(message: Message):
    reply = await get_coffee_quotes()
    await message.answer(reply)
    await log_interaction(message.from_user.id, message.text, reply)

# Регистрация всех хендлеров
def register_handlers(dp: Dispatcher):
    dp.message.register(start, F.text == "/start")
    dp.message.register(coffee_list, F.text == "/coffee_list")
    dp.message.register(coffee_image, F.text == "/coffee_image")
    dp.message.register(scrap_products, F.text == "/scrap_products")
    dp.message.register(coffee_quotes, F.text == "/coffee_quotes")