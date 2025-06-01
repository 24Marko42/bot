# configy.py
from pathlib import Path

API_TOKEN: str = '7758306646:AAFOsyuud1FHjYarIp3JTiIwUB9ik8539lA'
LOG_DIR: Path = Path("coffee_logs")
ADMIN_ID: int = 5071431292  # Замените на ваш ID в Telegram

TASTY_URL: str = "https://shop.tastycoffee.ru/coffee?page=2"
API_COFFEE_LIST_URL: str = "https://api.sampleapis.com/coffee/hot"
BASE_URL: str = "https://shop.tastycoffee.ru"

BREWING_TIPS: list[str] = [
    "1. Используйте свежемолотый кофе.",
    "2. Температура воды — 92‑96°C.",
    "3. Не заливайте кипятком — горечь!",
    "4. Пропорция: 60 г кофе на литр воды.",
    "5. Экспериментируйте с помолом.",
]