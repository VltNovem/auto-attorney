import os
import json
import re
from bs4 import BeautifulSoup

# Укажи точное имя файла
input_file = "/content/Про автомобільний транспорт - Закон № 2344-III від 05.04.2001 - d81073-20241115.htm"

# Функция для обработки HTML в структурированный JSON
def parse_law_html(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")

    # Извлекаем название закона из <title>
    title = soup.find("title").text.strip() if soup.find("title") else "Без назви"

    # Получаем основной текст закона из <div id="article">
    article_div = soup.find("div", {"id": "article"})
    if not article_div:
        print("❌ Не найден <div id='article'>. Парсинг невозможен.")
        return

    # Извлекаем номер и дату закона
    law_number = "Невідомий номер"
    law_date = "Невідома дата"
    match = re.search(r"від (\d{2}\.\d{2}\.\d{4}) № ([\dIVXLCDM-]+)", title)
    if match:
        law_date = match.group(1)
        law_number = match.group(2)

    # Функция для обработки вложенных списков
    def extract_list_items(ul_or_ol):
        items = []
        for li in ul_or_ol.find_all("li", recursive=False):  # Берем только верхний уровень
            sub_list = li.find(["ul", "ol"])  # Ищем вложенные списки
            if sub_list:
                items.append({
                    "text": li.get_text(strip=True),
                    "sub_list": extract_list_items(sub_list)  # Рекурсивный вызов
                })
            else:
                items.append(li.get_text(strip=True))
        return items

    # Обрабатываем содержимое, сохраняя структуру
    content = []
    for element in article_div.find_all(["h1", "h2", "h3", "p", "ul", "ol"]):
        text = element.get_text(strip=True)

        # Определяем заголовки
        if element.name in ["h1", "h2", "h3"]:
            content.append({"type": "heading", "level": int(element.name[1]), "text": text})

        # Определяем статьи и главы
        elif element.name == "p" and text:
            if re.match(r"^Стаття \d+", text):
                content.append({"type": "article", "text": text})
            elif re.match(r"^Розділ \d+", text):
                content.append({"type": "heading", "level": 1, "text": text})  # Раздел
            elif re.match(r"^Глава \d+", text):
                content.append({"type": "heading", "level": 2, "text": text})  # Глава
            else:
                content.append({"type": "paragraph", "text": text})

        # Определяем списки
        elif element.name in ["ul", "ol"]:
            list_type = "unordered" if element.name == "ul" else "ordered"
            list_items = extract_list_items(element)
            content.append({"type": "list", "list_type": list_type, "items": list_items})

    # Создаем JSON-структуру
    law_data = {
        "title": title,
        "law_number": law_number,
        "law_date": law_date,
        "content": content
    }

    # Определяем имя выходного файла
    json_filename = os.path.splitext(os.path.basename(file_path))[0] + ".json"
    output_path = os.path.join("/content/", json_filename)

    # Сохраняем JSON
    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(law_data, json_file, ensure_ascii=False, indent=4)
    
    print(f"✅ Обработан: {file_path} → {json_filename}")

# Запускаем парсер для указанного файла
parse_law_html(input_file)

print("🎉 Парсинг завершен! JSON-файл сохранен в /content/")
