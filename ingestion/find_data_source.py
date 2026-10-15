from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
html = (ROOT / "data" / "raw_page.html").read_text(encoding="utf-8")

keywords = ["ajax", "DataTable", "fetch(", "$.get", "$.post", "url:", "GoScheme", "api/"]

lines = html.splitlines()
print("Total lines in page:", len(lines))

for kw in keywords:
    print(f"\n=== Lines containing '{kw}' ===")
    count = 0
    for n, line in enumerate(lines, start=1):
        if kw.lower() in line.lower():
            print(f"{n}: {line.strip()[:200]}")
            count += 1
            if count >= 8:
                break
    if count == 0:
        print("(none)")