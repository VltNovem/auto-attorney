import json
from bs4 import BeautifulSoup

def parse_html_to_json(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract metadata
    title = soup.title.string if soup.title else "Без названия"
    law_number = extract_law_number(soup)
    law_date = extract_law_date(soup)
    source = extract_source(soup)

    # Extract content
    content = []
    headings = soup.find_all(['h1', 'h2', 'h3'])
    for heading in headings:
        level = int(heading.name[1])
        content.append({
            "type": "heading",
            "level": level,
            "text": heading.get_text(strip=True)
        })

    articles = soup.find_all('p', class_='article')
    for article in articles:
        content.append({
            "type": "article",
            "text": article.get_text(strip=True)
        })

    paragraphs = soup.find_all('p', class_='paragraph')
    for paragraph in paragraphs:
        content.append({
            "type": "paragraph",
            "text": paragraph.get_text(strip=True)
        })

    lists = soup.find_all(['ul', 'ol'])
    for list_tag in lists:
        list_type = 'unordered' if list_tag.name == 'ul' else 'ordered'
        items = [li.get_text(strip=True) for li in list_tag.find_all('li')]
        content.append({
            "type": "list",
            "list_type": list_type,
            "items": items
        })

    amendments = soup.find_all('p', class_='amendment')
    for amendment in amendments:
        content.append({
            "type": "amendment",
            "text": amendment.get_text(strip=True)
        })

    references = soup.find_all('p', class_='reference')
    for reference in references:
        law_number, law_date, text = extract_reference_details(reference)
        content.append({
            "type": "reference",
            "law_number": law_number,
            "law_date": law_date,
            "text": text
        })

    # Construct final JSON structure
    law_json = {
        "title": title,
        "law_number": law_number,
        "law_date": law_date,
        "source": source,
        "content": content
    }

    return json.dumps(law_json, ensure_ascii=False, indent=2)

def extract_law_number(soup):
    # Implement extraction logic for law number
    return "2344-III"

def extract_law_date(soup):
    # Implement extraction logic for law date
    return "05.04.2001"

def extract_source(soup):
    # Implement extraction logic for source
    return "http://example.com"

def extract_reference_details(reference):
    # Implement extraction logic for reference details
    law_number = "586-VI"
    law_date = "24.09.2008"
    text = reference.get_text(strip=True)
    return law_number, law_date, text

# Example usage
file_path = '/content/Про автомобільний транспорт - Закон № 2344-III від 05.04.2001 - d81073-20241115.htm'
with open(file_path, 'r', encoding='utf-8') as html_file:
    html_content = html_file.read()

json_content = parse_html_to_json(html_content)

output_path = '/content/output.json'
with open(output_path, 'w', encoding='utf-8') as json_file:
    json_file.write(json_content)

print("Парсинг завершен. JSON сохранен в", output_path)
