import re
import json
from bs4 import BeautifulSoup, NavigableString
import os  # Додаємо для роботи з файловою системою

def parse_npa_html(html_file_path):
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"Помилка: Файл '{html_file_path}' не знайдено!")
        return None  # Повертаємо None, якщо файлу немає
    except Exception as e:
        print(f"Помилка при читанні файлу '{html_file_path}': {e}")
        return None

    soup = BeautifulSoup(html_content, 'html.parser')

    # --- Метаданные ---
    title_tag = soup.find('title')
    title = title_tag.text.strip() if title_tag else "Название не найдено"

    law_number_match = re.search(r"№\s*([0-9A-Za-z/-]+)\s*", title)
    law_date_match = re.search(r"від\s*(\d{2}\.\d{2}\.\d{4})", title)

    law_number = law_number_match.group(1) if law_number_match else "Номер не найден"
    law_date = law_date_match.group(1) if law_date_match else "Дата не найдена"

    json_data = {
        "title": title,
        "law_number": law_number,
        "law_date": law_date,
        "source": None,
        "content": []
    }

    article_div = soup.find('div', id='article')
    if not article_div:
        print(f"Попередження: В файлі '{html_file_path}' не знайдено div з id='article'.")
        return json_data

    current_heading_levels = []
    in_list = False
    list_type = "unordered" #тип списку

    for element in article_div.descendants:  # Обходимо *всіх* нащадків
        if isinstance(element, NavigableString):  # Пропускаємо порожні текстові вузли
            if element.strip() == "":
                continue

        if element.name == 'p':
            text = element.get_text(separator=" ", strip=True)
            if not text:
                continue

             # --- Статьи (article) ---
            if text.startswith("Стаття"):
                json_data['content'].append({
                    "type": "article",
                    "text": text
                })
                in_list = False #скидання
                continue

             # --- Поправки (amendment) и Ссылки (reference) ---
            # (винесено перед обробкою списків, бо поправки можуть бути всередині списків)
            if element.find('em') and ("згідно із Законом" in text or "змінено Законом" in text or "виключено згідно із Законом" in text):
                 amendment_text = text
                 match = re.search(r"(№\s*[\w\d/-]+)\s*(?:від\s*(\d{2}\.\d{2}\.\d{4}))?", amendment_text) # ?: для необов'язковості
                 law_number = match.group(1) if match else None
                 law_date = match.group(2) if match else None
                 if law_number and law_date:
                    json_data['content'].append({
                        "type": "reference",
                        "law_number": law_number,
                        "law_date": law_date,
                        "text": amendment_text
                    })
                 else:
                    json_data['content'].append({
                         "type": "amendment",
                         "text": amendment_text
                     })
                 in_list = False
                 continue #переходимо до іншого тега

            elif element.find('a', href=True):
                link = element.find('a')
                href = link.get('href')
                link_text = element.get_text(strip=True)
                match = re.search(r"(№\s*[\w\d/-]+)\s*(?:від\s*(\d{2}\.\d{2}\.\d{4}))?", link_text)
                law_number = match.group(1) if match else None
                law_date = match.group(2) if match else None
                json_data['content'].append({
                  "type": "reference",
                  "law_number": law_number,
                  "law_date": law_date,
                  "text": link_text,
                  "url": href
                 })
                in_list = False
                continue #переходимо до іншого тега

            # --- Списки (list) ---
            elif 'rvps2' in element.get('class', []) or in_list:
                # Перевіряємо наявність списку:
                is_list_item = False
                #перевірка чи є нумерація:
                match_ordered = re.match(r'^\s*(\d+[\.\)]|\w\))', element.get_text(strip=True))
                if match_ordered:
                    is_list_item = True
                    if not in_list: #якщо список тільки почався:
                        list_type = "ordered"

                #Якщо це елемент списку:
                if 'rvps2' in element.get('class', []) or is_list_item:
                    is_list_item = True
                    if json_data['content'] and json_data['content'][-1]['type'] == 'list':
                        # Якщо поточний елемент - частина списку, додаємо його
                        list_item_text = element.get_text(strip=True)
                        if list_item_text: #перевірка
                            json_data['content'][-1]['items'].append(list_item_text)
                    else:
                      # Починаємо новий список
                      list_type = "ordered" if match_ordered else "unordered" #визначення типу
                      json_data['content'].append({
                            "type": "list",
                            "list_type": list_type,
                            "items": [element.get_text(strip=True)]
                      })
                    in_list = True #ми в списку
                    continue
                else:
                  in_list = False #якщо не частина списку, то скидуємо флаг
                  json_data['content'].append({
                    "type": "paragraph",
                    "text": text
                  })
            # --- Обычные абзацы (paragraph) ---
            else:
                json_data['content'].append({
                    "type": "paragraph",
                    "text": text
                })
                in_list = False

        # --- Заголовки (heading) ---
        elif element.name == 'span' and 'rvts15' in element.get('class', []):
            heading_text = element.get_text(strip=True)
            in_list = False #скидання

            if element.find_next_sibling('br'):
              next_span = element.find_next_sibling('span', class_='rvts15')
              if next_span:
                heading_text += " " + next_span.get_text(strip=True)

            if heading_text.startswith("Розділ"):
                level = 1
            elif heading_text.startswith("Глава"):
                level = 2
            else:
                level = 3
                parent_p = element.find_parent('p') #шукаємо батьківський
                if parent_p and 'rvps7' in parent_p.get('class', []):
                    level = 2
                else:
                  level = len(current_heading_levels) +1

            current_heading_levels = current_heading_levels[:level - 1]
            current_heading_levels.append(heading_text)

            json_data['content'].append({
                "type": "heading",
                "level": level,
                "text": heading_text
            })



        # --- Таблицы (table) ---
        elif element.name == 'table':
            in_list = False
            table_data = []
            for row in element.find_all('tr'):
                row_data = []
                for cell in row.find_all(['td', 'th']):
                    row_data.append(cell.get_text(strip=True))
                if row_data:
                  table_data.append(row_data)
            if table_data:
              json_data['content'].append({
                  "type": "table",
                  "data": table_data
              })


    return json_data


# --- Пример использования ---
file_paths = [
  "Про обов'язкове страхування цивільно-правової відповідальн… - Закон № 1961-IV від 01.07.2004 - d152096-20250101.htm",
  "Про дорожній рух - Закон № 3353-XII від 30.06.1993 - d21160-20250105.htm",
  "Про автомобільний транспорт - Закон № 2344-III від 05.04.2001 - d81073-20241115.htm"
]

for file_path in file_paths:
    # Перевірка, чи файл існує:
    if not os.path.exists(file_path):
        print(f"Файл '{file_path}' не знайдено. Пропускаємо.")
        continue  # Переходимо до наступного файлу

    json_output = parse_npa_html(file_path)
    if json_output:  # Перевіряємо, чи повернула функція результат
        output_file_name = file_path.replace(".htm", ".json")  # Змінив розширення
        try:
            with open(output_file_name, 'w', encoding='utf-8') as outfile:
                json.dump(json_output, outfile, ensure_ascii=False, indent=2)
            print(f"Файл {file_path} успішно перетворено в {output_file_name}")
        except Exception as e:
            print(f"Помилка при записі JSON у файл '{output_file_name}': {e}")
