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
            law_date = law_info[1].strip()
    
    # Основная структура документа
    law_data = {
        "title": title,
        "law_number": law_number,
        "law_date": law_date,
        "source": "",  # Добавим позже извлечение источника
        "content": []  # Здесь будет основное содержимое
    }
    
    # Получаем основной контент
    article_div = soup.find("div", {"id": "article"})
    if article_div:
        parse_content(article_div, law_data["content"])
    
    return law_data

def parse_content(element, content_list):
    # Здесь будет логика разбора контента
    pass

# Вспомогательные функции для определения типов контента
def is_heading(text):
    patterns = [
        r"^Розділ\s+[IVX]+\.?",
        r"^Глава\s+\d+\.?",
    ]
    return any(re.match(pattern, text.strip()) for pattern in patterns)

def get_heading_level(text):
    if re.match(r"^Розділ\s+[IVX]+\.?", text.strip()):
        return 1
    elif re.match(r"^Глава\s+\d+\.?", text.strip()):
        return 2
    return 3

def is_article(text):
    return bool(re.match(r"^Стаття\s+\d+\.?", text.strip()))
