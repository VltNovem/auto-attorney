import os
import json
from bs4 import BeautifulSoup
import re

def parse_law_html(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "lxml")
    
    # Базовые метаданные
    title = soup.find("title").text.strip() if soup.find("title") else "Без назви"
    
    # Извлекаем номер и дату закона
    law_number = "Невідомий номер"
    law_date = "Невідома дата"
    title_parts = title.split(" - Закон № ")
    if len(title_parts) > 1:
        law_info = title_parts[1].split(" від ")
        if len(law_info) == 2:
            law_number = law_info[0].strip()
            law_date = law_info[1].split(" - ")[0].strip()  # Убираем возможный суффикс с датой изменения
    
    # Основная структура документа
    law_data = {
        "title": title,
        "law_number": law_number,
        "law_date": law_date,
        "source": "",
        "content": []
    }
    
    # Получаем основной контент
    article_div = soup.find("div", {"id": "article"})
    if article_div:
        current_article = None
        current_list_items = []
        
        for element in article_div.find_all(['p', 'div', 'ul', 'ol']):
            text = element.get_text().strip()
            if not text:
                continue
                
            # Проверяем, является ли это заголовком
            if is_heading(text):
                # Закрываем текущий список, если есть
                if current_list_items:
                    law_data["content"].append({
                        "type": "list",
                        "list_type": "unordered",
                        "items": current_list_items.copy()
                    })
                    current_list_items = []
                
                law_data["content"].append({
                    "type": "heading",
                    "level": get_heading_level(text),
                    "text": text
                })
                continue
            
            # Проверяем, является ли это статьёй
            if is_article(text):
                # Закрываем текущий список, если есть
                if current_list_items:
                    law_data["content"].append({
                        "type": "list",
                        "list_type": "unordered",
                        "items": current_list_items.copy()
                    })
                    current_list_items = []
                
                law_data["content"].append({
                    "type": "article",
                    "text": text
                })
                continue
            
            # Проверяем, является ли это поправкой
            if is_amendment(text):
                # Закрываем текущий список, если есть
                if current_list_items:
                    law_data["content"].append({
                        "type": "list",
                        "list_type": "unordered",
                        "items": current_list_items.copy()
                    })
                    current_list_items = []
                
                law_data["content"].append(parse_amendment(text))
                continue
            
            # Проверяем, является ли это ссылкой на закон
            if is_reference(text):
                # Закрываем текущий список, если есть
                if current_list_items:
                    law_data["content"].append({
                        "type": "list",
                        "list_type": "unordered",
                        "items": current_list_items.copy()
                    })
                    current_list_items = []
                
                law_data["content"].append(parse_reference(text))
                continue
            
            # Обработка списков
            if element.name in ['ul', 'ol'] or element.get('class') == ['rvps2']:
                # Если это явный элемент списка или параграф с классом rvps2
                if not text in current_list_items:  # Избегаем дубликатов
                    current_list_items.append(text)
            else:
                # Если встретили не элемент списка, но есть накопленные элементы списка
                if current_list_items:
                    law_data["content"].append({
                        "type": "list",
                        "list_type": "unordered",
                        "items": current_list_items.copy()
                    })
                    current_list_items = []
                
                # Добавляем как обычный параграф
                law_data["content"].append({
                    "type": "paragraph",
                    "text": text
                })
    
    return law_data

def is_heading(text):
    patterns = [
        r"^Розділ\s+[IVX]+[\.\s]",
        r"^Глава\s+\d+[\.\s]",
        r"^I{1,3}V?X?\.\s+",  # Для заголовков вида "I.", "II.", "III." и т.д.
    ]
    return any(re.match(pattern, text.strip()) for pattern in patterns)

def get_heading_level(text):
    text = text.strip()
    if re.match(r"^Розділ\s+[IVX]+[\.\s]", text):
        return 1
    elif re.match(r"^Глава\s+\d+[\.\s]", text):
        return 2
    elif re.match(r"^I{1,3}V?X?\.\s+", text):
        return 2
    return 3

def is_article(text):
    return bool(re.match(r"^Стаття\s+\d+[\.\s]", text.strip()))

def is_amendment(text):
    patterns = [
        r"згідно із Законом",
        r"змінено Законом",
        r"доповнено Законом",
        r"виключено Законом",
        r"у редакції Закону"
    ]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

def parse_amendment(text):
    return {
        "type": "amendment",
        "text": text
    }

def is_reference(text):
    return bool(re.search(r"№\s*\d+-[A-ZІХ]+\s+від\s+\d{2}\.\d{2}\.\d{4}", text))

def parse_reference(text):
    match = re.search(r"№\s*(\d+-[A-ZІХ]+)\s+від\s+(\d{2}\.\d{2}\.\d{4})", text)
    if match:
        return {
            "type": "reference",
            "law_number": match.group(1),
            "law_date": match.group(2),
            "text": text
        }
    return {
        "type": "reference",
        "text": text
    }

# Запуск парсера
input_file = "/content/Про автомобільний транспорт - Закон № 2344-III від 05.04.2001 - d81073-20241115.htm"

# Парсим файл
law_data = parse_law_html(input_file)

# Создаем имя для выходного JSON файла
json_filename = os.path.splitext(os.path.basename(input_file))[0] + ".json"
output_path = os.path.join("/content/", json_filename)

# Сохраняем результат в JSON
with open(output_path, "w", encoding="utf-8") as json_file:
    json.dump(law_data, json_file, ensure_ascii=False, indent=2)

print(f"✅ Обработан: {input_file}")
print(f"✅ Создан файл: {output_path}")

# Проверка размеров
input_size = os.path.getsize(input_file)
output_size = os.path.getsize(output_path)

print(f"\nРазмер исходного HTML файла: {input_size:,} байт")
print(f"Размер созданного JSON файла: {output_size:,} байт")

with open(input_file, "r", encoding="utf-8") as file:
    html_content = file.read()
    print(f"Количество символов в HTML: {len(html_content):,}")

with open(output_path, "r", encoding="utf-8") as file:
    json_content = file.read()
    print(f"Количество символов в JSON: {len(json_content):,}")
