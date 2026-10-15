import requests
from bs4 import BeautifulSoup

URL = "https://www.tnagrisnet.tn.gov.in/people_app/GoScheme"
HEADERS = {"User-Agent": "Mozilla/5.0 (student RAG learning project)"}

resp = requests.get(URL, headers=HEADERS, timeout=30)
print("Status code:", resp.status_code)

# Save the raw HTML so we can work offline
with open("data/raw_page.html", "w", encoding="utf-8") as f:
    f.write(resp.text)

soup = BeautifulSoup(resp.text, "html.parser")

tables = soup.find_all("table")
print("Number of tables found:", len(tables))

for i, table in enumerate(tables):
    rows = table.find_all("tr")
    print(f"\nTable {i}: {len(rows)} rows (including header)")
    for row in rows[:3]:
        cells = [c.get_text(strip=True)[:40] for c in row.find_all(["th", "td"])]
        print("  ", cells)