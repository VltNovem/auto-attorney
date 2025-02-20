import os
import json
import re
from bs4 import BeautifulSoup

# Укажи точное имя файла
input_file = "/content/Про автомобільний транспорт - Закон № 2344-III від 05.04.2001 - d81073-20241115.htm"

# Функция парсинга HTML в JSON
def parse_law_html(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")

    # Извлекаем название закона из <title>
    title = soup.find("title").text.strip() if soup.find("title") else "Без назви"

    # Получаем основной текст закона из <div id="article">
    article_div = soup.find("div", {"id": "article"})
    text = article_div.get_text("\n").strip() if article_div else "Текст відсутній"

    # Извлекаем номер и дату закона с учетом нового формата
    law_number = "Невідомий номер"
    law_date = "Невідома дата"

    match = re.search(r"від (\d{2}\.\d{2}\.\d{4}) № ([\dIVXLCDM-]+)", title)
    if match:
        law_date = match.group(1)  # Дата закона
        law_number = match.group(2)  # Номер закона

    # Создаем JSON-структуру
    law_data = {
        "title": title,
        "law_number": law_number,
        "law_date": law_date,
        "text": text
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
