# Импорт необходимых модулей и классов
from datetime import datetime  # Для получения текущего времени
from pathlib import Path       # Для работы с файловыми путями
from typing import List, Union  # Для аннотаций типов (списки и объединения типов)
from aiogram.types import Message  # Тип сообщения из библиотеки aiogram
from aiogram.enums import ParseMode  # Для указания режима форматирования сообщений (HTML, Markdown и т.д.)

# Создание директории для логов, если она ещё не существует
LOG_DIR: Path = Path("coffee_logs")  # Папка, в которой будут храниться логи
LOG_DIR.mkdir(exist_ok=True)         # Создаёт папку, если она ещё не создана (не вызывает ошибку, если уже есть)

# Функция логирования входящих сообщений от пользователя
def log_message(message: Message) -> None:
    user = message.from_user  # Получение объекта пользователя, который отправил сообщение
    # Создание пути к лог-файлу с именем пользователя
    log_file = LOG_DIR / f"{user.first_name}_{user.username}.log"
    # Открытие лог-файла в режиме добавления ('a') с кодировкой UTF-8
    with open(log_file, "a", encoding="utf-8") as f:
        # Запись строки лога: время, имя, username, ID, текст сообщения
        f.write(
            f"{datetime.now().isoformat()} | "
            f"{user.first_name} | {user.username} | {user.id} | {message.text}\n"
        )

# Асинхронная функция, которая отправляет ответ пользователю и логирует его
async def send_and_log(message: Message, content: Union[str, List[str]]) -> None:
    user = message.from_user  # Получение пользователя, которому отправляется сообщение
    log_file = LOG_DIR / f"{user.first_name}_{user.username}.log"  # Путь к его лог-файлу

    # Вложенная функция логирования ответа бота
    def _log(entry: str):
        with open(log_file, "a", encoding="utf-8") as f:
            # Запись строки в лог: текущее время и текст, отправленный ботом
            f.write(f"{datetime.now().isoformat()} | Bot: {entry}\n")

    # Проверка, является ли content списком строк
    if isinstance(content, list):
        for text in content:
            # Отправка каждой строки пользователю с HTML-разметкой
            await message.answer(text, parse_mode=ParseMode.HTML)
            _log(text)  # Логирование каждой строки
    else:
        # Отправка одной строки
        await message.answer(content, parse_mode=ParseMode.HTML)
        _log(content)  # Логирование этой строки
