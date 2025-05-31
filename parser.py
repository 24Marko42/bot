import requests
from bs4 import BeautifulSoup

async def get_coffee_products():
    try:
        url = "https://shop.tastycoffee.ru/coffee"
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        items = soup.select(".product-card__content")[:5]
        products = []

        for item in items:
            name_tag = item.select_one(".product-card__title")
            price_tag = item.select_one(".price__value")
            if name_tag and price_tag:
                name = name_tag.get_text(strip=True)
                price = price_tag.get_text(strip=True)
                products.append(f"☕ {name} — {price} ₽")

        return "\n".join(products) if products else "❌ Не удалось найти товары."

    except Exception:
        return "⚠️ Ошибка при парсинге сайта."

async def get_coffee_quotes():
    try:
        url = "https://citaty.info/topic/kofe"
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        quotes = []
        for item in soup.select(".view-content .quote")[:5]:
            text_elem = item.select_one(".field-name-field-quote")
            author_elem = item.select_one(".field-name-field-author .field-item a")
            if text_elem and author_elem:
                text = text_elem.get_text(strip=True)
                author = author_elem.get_text(strip=True)
                quotes.append(f"💬 {text}\n— {author}\n")

        return "\n".join(quotes) if quotes else "❌ Не удалось найти цитаты."

    except Exception:
        return "❌ Ошибка при получении цитат."