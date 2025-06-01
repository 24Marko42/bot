# parsers.py

import random  # Для генерации случайных чисел
from typing import List, Optional  # Аннотации типов для лучшей читаемости
import aiohttp  # Асинхронные HTTP-запросы
from bs4 import BeautifulSoup  # Парсинг HTML-контента

# Базовые URL-адреса для работы парсера
BASE_URL: str = "https://shop.tastycoffee.ru"  # Основной домен сайта
TASTY_URL_TEMPLATE: str = "https://shop.tastycoffee.ru/coffee?page={}"  # Шаблон URL для страниц с кофе
API_COFFEE_LIST_URL: str = "https://api.sampleapis.com/coffee/hot"  # API для получения списка кофе

async def fetch_html(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    """
    Асинхронно загружает HTML-контент по указанному URL.
    
    Args:
        session: Сессия aiohttp для выполнения запросов
        url: URL для загрузки
        
    Returns:
        HTML-контент в виде строки или None при ошибке
    """
    try:
        # Выполняем GET-запрос с таймаутом 10 секунд
        async with session.get(url, timeout=10) as resp:
            if resp.status == 200:  # Проверяем успешный статус ответа
                return await resp.text()  # Возвращаем текст ответа
    except:
        return None  # Возвращаем None при любой ошибке

async def translate_text(text: str, dest: str = "ru") -> str:
    """
    Переводит текст на указанный язык с помощью Google Translate API.
    
    Args:
        text: Текст для перевода
        dest: Язык назначения (по умолчанию русский)
        
    Returns:
        Переведенный текст или оригинал при ошибке
    """
    import urllib.parse  # Импорт внутри функции для оптимизации
    
    try:
        # Кодируем текст для передачи в URL
        encoded = urllib.parse.quote(text)
        # Формируем URL для Google Translate API
        url = (
            f"https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=auto&tl={dest}&dt=t&q={encoded}"
        )
        
        # Создаем новую сессию для запроса
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:  # Проверяем успешность запроса
                    return text  # Возвращаем оригинал при ошибке
                
                # Парсим JSON-ответ
                arr = await resp.json()
                # Извлекаем переведенный текст из сложной структуры ответа
                if isinstance(arr, list) and arr and isinstance(arr[0], list):
                    return arr[0][0][0]  # Возвращаем переведенный текст
                else:
                    return text  # Возвращаем оригинал при неожиданной структуре
    except:
        return text  # Возвращаем оригинал при любой ошибке

async def parse_coffee_page(url: str, limit: int = 5) -> List[str]:
    """
    Парсит страницу с кофе и извлекает информацию о продуктах.
    
    Args:
        url: URL страницы с кофе
        limit: Максимальное количество продуктов для извлечения
        
    Returns:
        Список форматированных строк с информацией о продуктах
    """
    # Создаем сессию и загружаем HTML
    async with aiohttp.ClientSession() as session:
        html = await fetch_html(session, url)
        if not html:  # Проверяем успешность загрузки
            return ["❌ Ошибка при запросе к tastycoffee.ru"]

    # Парсим HTML с помощью BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    # Находим все элементы продуктов
    items = soup.select("div.product-item")
    results: List[str] = []  # Список для результатов

    # Обрабатываем каждый продукт до достижения лимита
    for idx, item in enumerate(items):
        if idx >= limit:
            break

        # Извлекаем название продукта
        title_tag = item.select_one("div.tc-tile__title a")
        if not title_tag:
            continue  # Пропускаем если нет названия
            
        name_en = title_tag.get_text(strip=True)  # Английское название
        name_ru = await translate_text(name_en, dest="ru")  # Переводим на русский
        rel_link = title_tag.get("href", "").strip()  # Относительная ссылка
        full_link = BASE_URL + rel_link  # Полная ссылка

        # Извлекаем цену
        price_tag = item.select_one("span.text-nowrap")
        price_text = price_tag.get_text(strip=True) if price_tag else "—"  # Текст цены

        # Извлекаем описание
        desc_container = item.select_one("div.tc-tile__description")
        if desc_container:
            description_p = desc_container.find("p", class_="text-[14px]")
            if description_p:
                # Получаем и переводим описание
                description_en = description_p.get_text(separator=" ", strip=True)
                description_ru = await translate_text(description_en, dest="ru")
            else:
                description_ru = ""  # Пустое описание, если не найдено
        else:
            description_ru = ""  # Пустое описание, если контейнера нет

        # Извлекаем вкусовые ноты
        notes_list = []
        if desc_container and description_p:
            # Находим все элементы с нотами вкуса
            for span in description_p.find_all("span", class_="descriptor-badge"):
                notes_list.append(span.get_text(strip=True))
        # Форматируем ноты в строку
        notes_text = ", ".join(notes_list) if notes_list else "—"

        # Форматируем результат для одного продукта
        results.append(
            f"☕ <b>{name_ru}</b>\n"
            f"💰 {price_text}\n"
            f"🔗 <a href=\"{full_link}\">Ссылка</a>\n\n"
            f"ℹ️ <i>{description_ru}</i>\n\n"
            f"Ноты вкуса: {notes_text}"
        )

    # Возвращаем результат или сообщение об отсутствии продуктов
    if not results:
        return ["ℹ️ Не удалось найти товары на странице."]
    return results

async def get_coffee_list() -> str:
    """
    Получает список популярных сортов кофе из API.
    
    Returns:
        Форматированная строка с названиями сортов
    """
    try:
        # Запрашиваем данные из API
        async with aiohttp.ClientSession() as session:
            async with session.get(API_COFFEE_LIST_URL) as resp:
                data = await resp.json()  # Парсим JSON-ответ
    except Exception as e:
        return f"Ошибка: {e}"  # Возвращаем ошибку при проблемах
    
    # Формируем заголовок
    lines = ["Популярные сорта:"]
    # Обрабатываем первые 10 элементов
    for item in data[:10]:
        en = item.get("title", "—")  # Английское название
        ru = await translate_text(en, dest="ru")  # Русское название
        lines.append(f"• {ru}")  # Добавляем в список
        
    # Объединяем все строки
    return "\n".join(lines)

async def get_coffee_random() -> str:
    """
    Получает случайный сорт кофе из API.
    
    Returns:
        Форматированная строка с информацией о случайном кофе
    """
    try:
        # Запрашиваем данные из API
        async with aiohttp.ClientSession() as session:
            async with session.get(API_COFFEE_LIST_URL) as resp:
                data = await resp.json()  # Парсим JSON-ответ
    except:
        return "Ошибка API"  # Сообщение об ошибке
    
    # Выбираем случайный элемент
    item = random.choice(data)
    # Извлекаем название и описание
    title = item.get("title", "—")
    desc = item.get("description", "—")
    # Переводим на русский
    title_ru = await translate_text(title, dest="ru")
    desc_ru = await translate_text(desc, dest="ru")
    
    # Форматируем результат
    return f"🎲 <b>{title_ru}</b>\n\n{desc_ru}"

async def get_all_flavor_notes() -> List[str]:
    """
    Собирает все уникальные вкусовые ноты со всех страниц сайта.
    
    Returns:
        Отсортированный список уникальных нот вкуса
    """
    page = 1
    notes_set = set()  # Множество для уникальных нот

    # Бесконечный цикл по страницам
    while True:
        # Формируем URL для текущей страницы
        url = TASTY_URL_TEMPLATE.format(page)
        async with aiohttp.ClientSession() as session:
            html = await fetch_html(session, url)
        if not html:  # Прерываем если не удалось загрузить
            break

        # Парсим HTML
        soup = BeautifulSoup(html, "html.parser")
        # Находим все продукты
        items = soup.select("div.product-item")
        if not items:  # Прерываем если нет продуктов
            break
        
        # Обрабатываем каждый продукт
        for item in items:
            # Находим контейнер описания
            desc_container = item.select_one("div.tc-tile__description")
            if not desc_container:
                continue  # Пропускаем если нет описания
                
            # Находим параграф с описанием
            description_p = desc_container.find("p")
            if not description_p:
                continue  # Пропускаем если нет параграфа
                
            # Извлекаем все ноты вкуса и добавляем в множество
            for span in description_p.select("span.descriptor-badge"):
                notes_set.add(span.get_text(strip=True).lower())  # В нижнем регистре
        
        page += 1  # Переход к следующей странице

    # Возвращаем отсортированный список уникальных нот
    return sorted(notes_set)

async def find_coffee_by_flavors(flavors: List[str]) -> List[str]:
    """
    Ищет кофе по заданным вкусовым нотам.
    
    Args:
        flavors: Список вкусовых нот для поиска
        
    Returns:
        Список форматированных строк с подходящими продуктами
    """
    page = 1
    results: List[str] = []  # Список для результатов

    # Очищаем и нормализуем вкусы (нижний регистр, без пробелов)
    user_flavors = [f.strip().lower() for f in flavors if f.strip()]

    # Бесконечный цикл по страницам
    while True:
        # Формируем URL для текущей страницы
        url = TASTY_URL_TEMPLATE.format(page)
        async with aiohttp.ClientSession() as session:
            html = await fetch_html(session, url)
        if not html:  # Прерываем если не удалось загрузить
            break

        # Парсим HTML
        soup = BeautifulSoup(html, "html.parser")
        # Находим все продукты
        items = soup.select("div.product-item")
        if not items:  # Прерываем если нет продуктов
            break

        # Обрабатываем каждый продукт
        for item in items:
            # Извлекаем название продукта
            title_tag = item.select_one("div.tc-tile__title a")
            if not title_tag:
                continue  # Пропускаем если нет названия

            # Получаем и переводим название
            name_en = title_tag.get_text(separator=" ", strip=True)
            name_ru = await translate_text(name_en, dest="ru")

            # Формируем полную ссылку
            link = BASE_URL + title_tag.get("href", "")

            # Извлекаем цену
            price_tag = item.select_one("span.text-nowrap")
            price_text = price_tag.get_text(strip=True) if price_tag else "—"  # Текст цены

            # Извлекаем описание
            desc_container = item.select_one("div.tc-tile__description")
            if not desc_container:
                continue  # Пропускаем если нет описания
                
            # Находим параграф с описанием
            description_p = desc_container.find("p", class_="text-[14px]")
            if not description_p:
                continue  # Пропускаем если нет параграфа
                
            # Получаем и переводим описание
            description_en = description_p.get_text(separator=" ", strip=True)
            description_ru = await translate_text(description_en, dest="ru")

            # Извлекаем все ноты вкуса (в нижнем регистре)
            notes = [s.get_text(strip=True).lower() for s in description_p.select("span.descriptor-badge")]

            # Проверяем соответствие всем запрошенным вкусам
            match = True
            for uf in user_flavors:
                words = uf.split()  # Разбиваем вкус на слова
                found_this_flavor = False
                
                # Проверяем каждую ноту продукта
                for note in notes:
                    # Проверяем содержит ли нота все слова вкуса
                    if all(word in note for word in words):
                        found_this_flavor = True
                        break
                
                # Если хоть один вкус не найден - продукт не подходит
                if not found_this_flavor:
                    match = False
                    break

            # Если продукт соответствует всем вкусам - добавляем в результаты
            if match:
                results.append(
                    f"☕ <b>{name_ru}</b>\n"
                    f"Вкусы: {', '.join(notes)}\n"
                    f"💰 Цена: {price_text}\n"
                    f"ℹ️ <i>{description_ru}</i>\n\n"
                    f"🔗 <a href=\"{link}\">Ссылка</a>"
                )

        page += 1  # Переход к следующей странице

    # Возвращаем результаты или сообщение об отсутствии совпадений
    return results or ["Совпадений не найдено."]