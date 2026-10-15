from pathlib import Path
import json
import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

PAGE_URL = "https://www.tnagrisnet.tn.gov.in/people_app/GoScheme"
API_URL = "https://www.tnagrisnet.tn.gov.in/people_app/goScheme/pending_ajax_list"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (student RAG learning project)",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": PAGE_URL,
}

payload = {
    "draw": 1,
    "start": 0,
    "length": 30,   # ask for 30 rows
    "dept": "",     # empty = all departments
    "scheme": "",   # empty = all schemes
}

resp = requests.post(API_URL, data=payload, headers=HEADERS, timeout=30)
print("Status code:", resp.status_code)

try:
    result = resp.json()
except ValueError:
    print("Response was not JSON. First 500 characters:")
    print(resp.text[:500])
    raise SystemExit

# Save the raw response so we can work offline
out_file = DATA_DIR / "raw_api_response.json"
out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("Saved to:", out_file)

print("\nTop-level keys:", list(result.keys()))
print("recordsTotal:", result.get("recordsTotal"))
print("recordsFiltered:", result.get("recordsFiltered"))

rows = result.get("data", [])
print("Rows returned:", len(rows))

for row in rows[:2]:
    print("\n--- Sample row ---")
    print(row)