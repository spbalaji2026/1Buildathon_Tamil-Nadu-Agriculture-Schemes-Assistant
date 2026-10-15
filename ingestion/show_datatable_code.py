from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
lines = (ROOT / "data" / "raw_page.html").read_text(encoding="utf-8").splitlines()

# Print lines 775 to 860 with line numbers
for n in range(774, 860):
    if n < len(lines):
        print(f"{n+1}: {lines[n]}")