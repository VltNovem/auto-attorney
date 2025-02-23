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

    # Обрабатываем содержимое, сохраняя структуру
    content = []
    list_items = []  # Временный буфер для списков
    list_type = None  # Тип списка (unordered или ordered)

    for element in article_div.find_all(["h1", "h2", "h3", "p", "ul", "ol"]):
        text = element.get_text(strip=True)

        # Проверяем, является ли элемент заголовком (включая <p class="rvps3"> и <p class="rvps4">)
        if element.name in ["h1", "h2", "h3"] or (element.name == "p" and element.get("class") in [["rvps3"], ["rvps4"]]):
            if list_items:  # Закрываем список, если он был
                content.append({"type": "list", "list_type": list_type, "items": list_items})
                list_items = []  # Очищаем буфер
            level = 1 if element.name == "h1" else (2 if element.name == "h2" else 3)
            content.append({"type": "heading", "level": level, "text": text})

        # Проверяем, является ли элемент статьей
        elif element.name == "p" and re.match(r"^Стаття \d+", text):
            if list_items:
                content.append({"type": "list", "list_type": list_type, "items": list_items})
                list_items = []
            content.append({"type": "article", "text": text})

        # Проверяем, является ли элемент частью списка (<p class="rvps2">)
        elif element.name == "p" and element.get("class") == ["rvps2"]:
            if not list_items:
                list_type = "ordered" if re.match(r"^\d+[\.\)]", text) else "unordered"
            list_items.append(text)

        # Проверяем, является ли элемент списком <ul> или <ol>
        elif element.name in ["ul", "ol"]:
            if list_items:
                content.append({"type": "list", "list_type": list_type, "items": list_items})
                list_items = []
            list_type = "unordered" if element.name == "ul" else "ordered"
            list_items = [li.get_text(strip=True) for li in element.find_all("li")]
            content.append({"type": "list", "list_type": list_type, "items": list_items})
            list_items = []

        # Проверяем, является ли элемент поправкой (amendment)
        elif re.search(r"(згідно із Законом № \d+-[IVXLCDM]+ від \d{2}\.\d{2}\.\d{4})", text):
            if list_items:
                content.append({"type": "list", "list_type": list_type, "items": list_items})
                list_items = []
            content.append({"type": "amendment", "text": text})

        # Проверяем, является ли элемент ссылкой на другой закон (reference)
        elif re.search(r"Законом № (\d+-[IVXLCDM]+) від (\d{2}\.\d{2}\.\d{4})", text):
            match = re.search(r"Законом № (\d+-[IVXLCDM]+) від (\d{2}\.\d{2}\.\d{4})", text)
            if list_items:
                content.append({"type": "list", "list_type": list_type, "items": list_items})
                list_items = []
            content.append({
                "type": "reference",
                "law_number": match.group(1),
                "law_date": match.group(2),
                "text": text
            })

        # Если это обычный текст
        else:
            if list_items:
                content.append({"type": "list", "list_type": list_type, "items": list_items})
                list_items = []
            content.append({"type": "paragraph", "text": text})

    # Если в конце обработки остался открытый список, добавляем его в контент
    if list_items:
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
