import os
import json
from bs4 import BeautifulSoup

# Укажи точное имя файла
input_file = "/content/Про автомобільний транспорт - Закон № 2344-III від 05.04.2001 - d81073-20241115.htm"

# Функция для определения типа списка
def detect_list_type(text):
    text = text.strip()
    if text.startswith(("1)", "2)", "3)", "4)", "5)")) or text[0].isdigit() and text[1] == ".":
        return "ordered"
    elif text.startswith(("а)", "б)", "в)", "г)", "д)")):
        return "unordered"
    return None

# Функция парсинга HTML в JSON
def parse_law_html(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "lxml")

    title = soup.find("title").text.strip() if soup.find("title") else "Без назви"

    article_div = soup.find("div", {"id": "article"})
    paragraphs = article_div.find_all("p") if article_div else []

    content = []
    current_list = None

    for p in paragraphs:
        text = p.get_text(strip=True)
        
        if not text:
            continue
        
        # Проверяем, является ли элемент списком
        list_type = detect_list_type(text)
        
        if list_type:
            if current_list and current_list["list_type"] == list_type:
                current_list["items"].append(text)
            else:
                if current_list:
                    content.append(current_list)
                current_list = {
                    "type": "list",
                    "list_type": list_type,
                    "items": [text]
                }
        else:
            if current_list:
                content.append(current_list)
                current_list = None
            content.append({
                "type": "paragraph",
                "text": text
            })

    if current_list:
        content.append(current_list)

    law_data = {
        "title": title,
        "law_number": "2344-III",
        "law_date": "05.04.2001",
        "content": content
    }

    json_filename = os.path.splitext(os.path.basename(file_path))[0] + ".json"
    output_path = os.path.join("/content/", json_filename)

    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(law_data, json_file, ensure_ascii=False, indent=4)
    
    print(f"✅ Обработан: {file_path} → {json_filename}")

parse_law_html(input_file)
print("🎉 Парсинг завершен! JSON-файл сохранен в /content/")
