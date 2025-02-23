import os
import json
import re
from bs4 import BeautifulSoup

# Укажи точное имя файла
input_file = "/content/Про автомобільний транспорт - Закон № 2344-III від 05.04.2001 - d81073-20241115.htm"

# Функция парсинга HTML в JSON
def parse_law_html(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "lxml")

    # Извлекаем название закона из <title>
    title = soup.find("title").text.strip() if soup.find("title") else "Без назви"

    # Извлекаем номер и дату закона
    law_number = "Невідомий номер"
    law_date = "Невідома дата"
    title_match = re.search(r"№ (\d+-[IVX]+) від (\d{2}\.\d{2}\.\d{4})", title)
    if title_match:
        law_number, law_date = title_match.groups()

    # Получаем основной текст закона
    article_div = soup.find("div", {"id": "article"})
    if not article_div:
        print("⚠️ Основной текст закона не найден!")
        return

    # Разбираем содержимое
    content = []
    current_list = None
    list_type = None

    for element in article_div.find_all(["p", "b", "a"]):
        text = element.get_text(strip=True)

        # Пропускаем пустые элементы
        if not text:
            continue

        # Обнаружение заголовков
        if element.name == "b":
            content.append({"type": "heading", "level": 2, "text": text})
            continue

        # Обнаружение нумерованных и маркированных списков
        if element.name == "p" and "rvps2" in element.get("class", []):
            match_numbered = re.match(r"^(\d+(\.\d+)*)\)", text)  # 1), 1.1), 1.2)
            match_lettered = re.match(r"^([а-я])\)", text)  # а), б)

            if match_numbered:
                if not current_list or list_type != "ordered":
                    if current_list:
                        content.append({"type": "list", "list_type": list_type, "items": current_list})
                    current_list = []
                    list_type = "ordered"
                current_list.append(text)

            elif match_lettered:
                if not current_list or list_type != "ordered":
                    if current_list:
                        content.append({"type": "list", "list_type": list_type, "items": current_list})
                    current_list = []
                    list_type = "ordered"
                current_list.append(text)

            else:
                if not current_list or list_type != "unordered":
                    if current_list:
                        content.append({"type": "list", "list_type": list_type, "items": current_list})
                    current_list = []
                    list_type = "unordered"
                current_list.append(text)

            continue

        # Проверка изменений в законе
        if "згідно із Законом" in text:
            content.append({"type": "amendment", "text": text})
            continue

        # Добавляем обычные параграфы
        content.append({"type": "paragraph", "text": text})

    # Завершаем обработку последнего списка
    if current_list:
        content.append({"type": "list", "list_type": list_type, "items": current_list})

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
