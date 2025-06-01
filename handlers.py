# Импорты стандартных и внешних библиотек
import asyncio
from aiogram import Bot, Dispatcher, types  # Основные компоненты aiogram
from aiogram.enums import ParseMode          # Для указания режима форматирования сообщений
from aiogram.filters.command import Command  # Для фильтрации сообщений по командам
from aiogram.fsm.state import State, StatesGroup  # Для описания состояний FSM
from aiogram.fsm.context import FSMContext         # Контекст для работы с FSM
from aiogram.types import Message                 # Тип сообщения Telegram

# Импорт настроек и вспомогательных модулей
from conf import coffee_bot_token, admin_id
from keyboards import MAIN_KEYBOARD, BREWING_TIPS
from log_utils import log_message, send_and_log
from parsers import (                          # Функции парсинга с сайта
    parse_coffee_page,
    get_coffee_list,
    get_coffee_random,
    get_all_flavor_notes,
    find_coffee_by_flavors,
)

# Переменные токена и ID администратора
API_TOKEN: str = coffee_bot_token
ADMIN_ID: int = admin_id

# Подключение памяти для FSM (Finite State Machine)
from aiogram.fsm.storage.memory import MemoryStorage
storage = MemoryStorage()

# Инициализация бота и диспетчера с FSM-хранилищем
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=storage)

# Определение группы состояний для FSM — режим "Предложка"
class Suggestion(StatesGroup):
    waiting_for_suggestion = State()

# Состояния для подбора кофе по вкусам
class FlavorSearch(StatesGroup):
    waiting_for_flavors = State()

# Обработка команды /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    log_message(message)  # Логируем входящее сообщение
    text = "Привет! Я бот про кофе ☕\nВыбирайте действие через кнопки ниже."
    await message.answer(text, reply_markup=MAIN_KEYBOARD)  # Приветствие + показ клавиатуры

# Обработка кнопки "ℹ️ Предложка"
@dp.message(lambda m: m.text == "ℹ️ Предложка")
async def ask_suggestion(message: Message, state: FSMContext):
    log_message(message)
    text = "📩 Напишите, пожалуйста, ваше предложение или замечание."
    await message.answer(text)  # Просим пользователя ввести предложение
    await state.set_state(Suggestion.waiting_for_suggestion)  # Переход в состояние ожидания

# Обработка ввода предложения от пользователя
@dp.message(Suggestion.waiting_for_suggestion)
async def process_suggestion(message: Message, state: FSMContext):
    log_message(message)
    user = message.from_user
    forwarded_text = (
        f"📨 Новая предложка от @{user.username or user.first_name} (ID: {user.id}):\n\n"
        f"{message.text}"
    )
    await bot.send_message(ADMIN_ID, forwarded_text)  # Пересылаем сообщение админу
    await message.answer("✅ Спасибо! Ваше предложение отправлено.")  # Ответ пользователю
    await state.clear()  # Очистка состояния FSM

# Обработка кнопки "📦 Последние сорта"
@dp.message(lambda m: m.text == "📦 Последние сорта")
async def latest_coffee(message: Message):
    log_message(message)
    # Получаем список сортов с сайта и отправляем пользователю
    await send_and_log(message, await parse_coffee_page("https://shop.tastycoffee.ru/coffee?page=1"))

# Обработка кнопки "🎲 Случайный кофе"
@dp.message(lambda m: m.text == "🎲 Случайный кофе")
async def random_coffee(message: Message):
    log_message(message)
    await send_and_log(message, await get_coffee_random())  # Отправка случайного кофе

# Обработка кнопки "📋 Список напитков"
@dp.message(lambda m: m.text == "📋 Список напитков")
async def coffee_list(message: Message):
    log_message(message)
    await send_and_log(message, await get_coffee_list())  # Отправка полного списка

# Обработка кнопки "☕ Советы"
@dp.message(lambda m: m.text == "☕ Советы")
async def brewing_tips(message: Message):
    log_message(message)
    await send_and_log(message, "\n".join(BREWING_TIPS))  # Отправка списка советов

# Обработка кнопки "🧪 Подбор по вкусам"
@dp.message(lambda m: m.text == "🧪 Подбор по вкусам")
async def select_flavors(message: Message, state: FSMContext):
    log_message(message)
    notes = await get_all_flavor_notes()  # Получаем все доступные вкусы
    if not notes:
        await message.answer("Не удалось получить список вкусов 😔")
        return
    # Инструкции по использованию + список вкусов
    await message.answer(
        "Доступные вкусы:\n" + ", ".join(notes) +
        "\n\nℹ️ Если вы используете «Подбор по вкусам», старайтесь вводить нотки в родительном падеже:\n"
        "например: «красного яблока», «молочного шоколада», «ореховой пасты» и т. п.\n"
        "(Так бот лучше найдёт совпадения.)"
    )
    await message.answer("Введите нужные вкусы через запятую:")  # Просим ввести вкусы
    await state.set_state(FlavorSearch.waiting_for_flavors)  # Переход в состояние ожидания ввода вкусов

# Обработка введённых пользователем вкусов
@dp.message(FlavorSearch.waiting_for_flavors)
async def process_flavors(message: Message, state: FSMContext):
    log_message(message)
    # Обработка ввода: разделяем по запятой, убираем лишнее
    flavors = [f.strip().lower() for f in message.text.split(",") if f.strip()]
    if not flavors:
        await message.answer("Не распознаны вкусы. Повторите ввод:")
        return
    # Поиск и отправка кофе по вкусам
    await send_and_log(message, await find_coffee_by_flavors(flavors))
    await state.clear()  # Очистка состояния FSM после завершения
