import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict

# Базовый домен, чтобы собрать абсолютный URL
BASE_URL = "https://shop.tastycoffee.ru"

async def parse_coffee_page(url: str) -> List[Dict]:
    """
    Асинхронно скачивает страницу по заданному URL и возвращает список словарей:
      - name         : название товара (строка)
      - link         : полный URL на страницу товара
      - description  : весь текст из <p class="text-[14px] ...">…</p>
      - flavor_notes : список строк — тексты из всех <span class="descriptor-badge">…</span>
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return []
                html = await resp.text()
        except Exception:
            return []

    soup = BeautifulSoup(html, "html.parser")
    products: List[Dict] = []

    # Находим все контейнеры товаров:
    # <div class="product tc-tile-col col-span-12 md:col-span-6 product-item" ...>
    for item in soup.select("div.product-item"):
        # 1) Название и относительная ссылка
        title_tag = item.select_one("div.tc-tile__title a")
        if not title_tag:
            continue

        name = title_tag.get_text(strip=True)
        rel_link = title_tag.get("href", "").strip()
        # Строим полный URL
        link = BASE_URL + rel_link

        # 2) Блок описания: <div class="tc-tile__description ...">
        desc_container = item.select_one("div.tc-tile__description")
        if desc_container:
            # В нём ищем тег <p> с class="text-[14px] leading-[20px] m-0"
            # Вместо CSS-селектора "p.text-[14px]" используем find по точному class_
            description_p = desc_container.find("p", class_="text-[14px]")
            if description_p:
                # Весь текст внутри <p> (собираем даже запятые и союз "и")
                description = description_p.get_text(separator=" ", strip=True)
                # Находим все <span class="descriptor-badge">…</span> внутри этого <p>
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

        products.append({
            "name": name,
            "link": link,
            "description": description,
            "flavor_notes": flavor_notes
        })

    return products

import asyncio

async def main():
    url = "https://shop.tastycoffee.ru/coffee?page=2"
    items = await parse_coffee_page(url)

    for prod in items:
        print("Название:    ", prod["name"])
        print("Ссылка:      ", prod["link"])
        print("Описание:    ", prod["description"])
        print("Ноты вкуса:  ", ", ".join(prod["flavor_notes"]))
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
