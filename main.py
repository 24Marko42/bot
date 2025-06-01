# main.py

# Импортируем модуль asyncio для работы с асинхронными функциями
import asyncio

# Импортируем класс Bot из библиотеки aiogram для работы с Telegram Bot API
from aiogram import Bot

# Импортируем диспетчер (dp) из файла handlers.py
# Диспетчер отвечает за обработку входящих сообщений и команд
from handlers import dp

# Импортируем токен бота из конфигурационного файла conf.py
from conf import coffee_bot_token

# Сохраняем токен бота в переменную API_TOKEN
API_TOKEN = coffee_bot_token

# Главная асинхронная функция для запуска бота
async def main():
    # Создаем экземпляр бота с указанным токеном
    bot = Bot(token=API_TOKEN)
    
    # Выводим сообщение о запуске бота в консоль
    print("Кофе-бот запущен...")
    
    # Запускаем бота в режиме постоянного опроса серверов Telegram
    # skip_updates=True - игнорировать сообщения, полученные пока бот был офлайн
    await dp.start_polling(bot, skip_updates=True)

# Точка входа в программу
if __name__ == "__main__":
    # Запускаем асинхронную функцию main() с помощью asyncio.run()
    asyncio.run(main())