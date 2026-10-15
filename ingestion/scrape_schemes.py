from pathlib import Path
import json
import re
import time
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

PAGE_URL = "https://www.tnagrisnet.tn.gov.in/people_app/GoScheme"
API_URL = "https://www.tnagrisnet.tn.gov.in/people_app/goScheme/pending_ajax_list"
PAGE_SIZE = 25

HEADERS = {
    "User-Agent": "Mozilla/5.0 (student RAG learning project)",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": PAGE_URL,
}


def clean_text(value):
    """Remove HTML tags and extra whitespace from any cell value."""
    text = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def extract_scheme_id(html_cell):
    """Pull the number out of onClick="getSchemeDet(147)"."""
    match = re.search(r"getSchemeDet\((\d+)\)", str(html_cell))
    return match.group(1) if match else None


def normalize_name(name):
    """Lowercase, drop punctuation and extra spaces, so near-identical names match."""
    name = name.lower().replace("’", "").replace("'", "")
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def fetch_all_rows():
    """Fetch every row from the server, one page at a time."""
    all_rows = []
    start = 0
    total = None
    draw = 1
    while total is None or start < total:
        payload = {"draw": draw, "start": start, "length": PAGE_SIZE, "dept": "", "scheme": ""}
        resp = requests.post(API_URL, data=payload, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        total = int(result.get("recordsTotal", 0))
        rows = result.get("data", [])
        if not rows:
            break
        all_rows.extend(rows)
        print(f"Fetched rows {start + 1} to {start + len(rows)} of {total}")
        start += PAGE_SIZE
        draw += 1
        time.sleep(1)  # be polite to the government server
    return all_rows


def row_to_scheme(row):
    return {
        "scheme_id": extract_scheme_id(row[2]),
        "department": clean_text(row[1]),
        "scheme_name": clean_text(row[2]),
        "description": clean_text(row[3]),
        "eligibility": clean_text(row[4]),
        "documents_required": clean_text(row[5]),
        "go_guidelines": clean_text(row[6]),
    }


def richness(scheme):
    """How much information a record holds (used to pick the better duplicate)."""
    return sum(len(str(scheme[k])) for k in
               ("description", "eligibility", "documents_required"))


def remove_duplicates(schemes):
    kept = {}      # key -> scheme
    removed = []   # (dropped scheme, reason)
    for s in schemes:
        keys = []
        if s["scheme_id"]:
            keys.append("id:" + s["scheme_id"])
        keys.append("name:" + normalize_name(s["scheme_name"]))

        match = next((k for k in keys if k in kept), None)
        if match is None:
            for k in keys:
                kept[k] = s
        else:
            existing = kept[match]
            if richness(s) > richness(existing):
                removed.append((existing, match))
                for k, v in list(kept.items()):
                    if v is existing:
                        kept[k] = s
                for k in keys:
                    kept[k] = s
            else:
                removed.append((s, match))

    unique, seen = [], set()
    for s in kept.values():
        if id(s) not in seen:
            seen.add(id(s))
            unique.append(s)
    return unique, removed

from difflib import SequenceMatcher


def is_junk(s):
    """Test/placeholder entries that are not real schemes."""
    name = normalize_name(s["scheme_name"])
    dept = s["department"].strip().lower()
    return name in ("", "tester", "test") or dept in ("", "none")


def report_near_duplicates(schemes, threshold=0.85):
    """Print pairs of similar names for manual review (nothing is deleted)."""
    print("\nNear-duplicate check (for your review, nothing removed):")
    found = False
    for i in range(len(schemes)):
        for j in range(i + 1, len(schemes)):
            a, b = schemes[i], schemes[j]
            ratio = SequenceMatcher(
                None, normalize_name(a["scheme_name"]), normalize_name(b["scheme_name"])
            ).ratio()
            if ratio >= threshold:
                found = True
                same_content = (a["description"] == b["description"]
                                and a["eligibility"] == b["eligibility"]
                                and a["documents_required"] == b["documents_required"])
                print(f'\n  Similarity {ratio:.2f}')
                print(f'   #{a["s_no"]} id={a["scheme_id"]} [{a["department"]}] {a["scheme_name"]}')
                print(f'   #{b["s_no"]} id={b["scheme_id"]} [{b["department"]}] {b["scheme_name"]}')
                print(f'   Identical description/eligibility/documents: {same_content}')
    if not found:
        print("  None found.")



def main():
    rows = fetch_all_rows()
    schemes = [row_to_scheme(r) for r in rows]
    print(f"\nRows fetched: {len(schemes)}")

    # Step 1: remove junk/test entries
    junk = [s for s in schemes if is_junk(s)]
    schemes = [s for s in schemes if not is_junk(s)]
    print(f"Junk/test entries removed: {len(junk)}")

    # Step 2: remove true duplicates (same ID or same normalized name)
    unique, removed = remove_duplicates(schemes)
    print(f"Real duplicates removed: {len(removed)}")
    for s, why in removed:
        print(f'  - dropped "{s["scheme_name"][:70]}" (matched {why})')

    for i, s in enumerate(unique, start=1):
        s["s_no"] = i

    out_file = DATA_DIR / "schemes.json"
    out_file.write_text(json.dumps(unique, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {len(unique)} unique schemes to {out_file}\n")

    for s in unique:
        flag = "   <-- short description" if len(s["description"]) < 60 else ""
        print(f'{s["s_no"]:>2}. [{s["department"]}] {s["scheme_name"][:60]}{flag}')

    report_near_duplicates(unique)

if __name__ == "__main__":
    main()