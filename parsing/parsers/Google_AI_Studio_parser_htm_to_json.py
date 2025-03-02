import re
import json
from bs4 import BeautifulSoup, NavigableString
import os

def parse_npa_html(html_file_path):
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"Помилка: Файл '{html_file_path}' не знайдено!")
        return None
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
    in_list = False  # Чи знаходимося ми зараз всередині списку
    list_type = "unordered"

    for element in article_div.descendants:
        if isinstance(element, NavigableString):
            if element.strip() == "":
                continue

        if element.name == 'p':
            text = element.get_text(separator=" ", strip=True)
            if not text:
                continue

            # --- Статті (article) ---
            if text.startswith("Стаття"):
                json_data['content'].append({
                    "type": "article",
                    "text": text
                })
                in_list = False  # Скидаємо стан списку
                continue # перехід на наступну ітерацію

            # --- Поправки (amendment) і Посилання (reference) ---
            # (винесено перед обробкою списків, бо поправки можуть бути *всередині* списків)
            if element.find('em') and ("згідно із Законом" in text or "змінено Законом" in text or "виключено згідно із Законом" in text):
                amendment_text = text
                match = re.search(r"(№\s*[\w\d/-]+)\s*(?:від\s*(\d{2}\.\d{2}\.\d{4}))?", amendment_text)
                law_number = match.group(1) if match else None
                law_date = match.group(2) if match else None
                if law_number and law_date:
                    json_data['content'].append({
                        "type": "reference",
                        "law_number": law_number,
                        "law_date": law_date,
                        "text": amendment_text
                    })
                else: #якщо не вдалося витягнути номер
                  json_data['content'].append({
                      "type": "amendment",
                      "text": amendment_text
                })
                in_list = False
                continue

            elif element.find('a', href=True):  # Посилання
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
            is_list_item = False  # Прапорець, чи є поточний елемент елементом списку

            # Перевірка, чи є нумерація (1., 1), а), і т.д.) або маркер (•, -, *)
            if 'rvps2' in element.get('class', []):
              is_list_item = True
            else:
              prev_p = element.find_previous_sibling('p')
              if prev_p and prev_p.get_text(strip=True).endswith(':'):
                is_list_item = True
              elif re.match(r'^\s*(\d+[\.\)]|\w\))', text): #перевірка на нумерацію
                is_list_item = True


            if is_list_item:  # Якщо це елемент списку
                if in_list:
                    # Якщо поточний елемент - частина списку, додаємо його
                    list_item_text = text
                    if list_item_text:
                        json_data['content'][-1]['items'].append(list_item_text)
                else:
                  # Починаємо новий список
                  list_type = "ordered" if re.match(r'^\s*(\d+[\.\)]|\w\))', text) else "unordered"
                  json_data['content'].append({
                        "type": "list",
                        "list_type": list_type,
                        "items": [text]
                  })
                in_list = True #зміна стану
                continue  # Переходимо до наступного елемента

            else:
                in_list = False  # Скидаємо прапорець, якщо це не елемент списку
                json_data['content'].append({  # Додаємо звичайний параграф
                    "type": "paragraph",
                    "text": text
                })


        # --- Заголовки (heading) ---
        elif element.name == 'span' and 'rvts15' in element.get('class', []):
            heading_text = element.get_text(strip=True)
            in_list = False

            # Об'єднуємо текст, якщо є <br> всередині заголовка
            if element.find_next_sibling('br'):
                next_span = element.find_next_sibling('span', class_='rvts15')
                if next_span:
                    heading_text += " " + next_span.get_text(strip=True)

            if heading_text.startswith("Розділ"):
                level = 1
            elif heading_text.startswith("Глава"):
                level = 2
            else:
              # Перевірка на заголовки всередині <p class="rvps7">
              level = 3
              parent_p = element.find_parent('p')
              if parent_p and 'rvps7' in parent_p.get('class', []):
                  level = 2 #якщо є rvps7 то це глава
              else:
                  for ancestor in element.parents:
                      if ancestor.name == 'p' and ancestor.find('span', class_='rvts15'): #шукаємо батьківський
                          level = len(current_heading_levels) +1
                          break

            current_heading_levels = current_heading_levels[:level - 1]
            current_heading_levels.append(heading_text)

            json_data['content'].append({
                "type": "heading",
                "level": level,
                "text": heading_text
            })


        # --- Таблицы (table) ---
        elif element.name == 'table':
            in_list = False  # Скидаємо стан списку
            table_data = []
            for row in element.find_all('tr'):
                row_data = []
                for cell in row.find_all(['td', 'th']):
                    row_data.append(cell.get_text(strip=True))
                if row_data:  # Додаємо, якщо рядок не порожній
                    table_data.append(row_data)
            if table_data:  # Якщо таблиця не порожня
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
