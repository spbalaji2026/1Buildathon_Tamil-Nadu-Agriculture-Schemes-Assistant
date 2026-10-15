import json
from pathlib import Path
from validator import validate_answer

ROOT = Path(__file__).resolve().parent.parent
schemes = json.loads((ROOT / "data" / "schemes.json").read_text(encoding="utf-8"))
s = next(x for x in schemes if x["scheme_id"] == "74")

source = (f"Scheme: {s['scheme_name']}\nDepartment: {s['department']}\n"
          f"Description: {s['description']}\nEligibility: {s['eligibility']}\n"
          f"Documents required: {s['documents_required']}")

print("=== SOURCE TEXT FOR SCHEME 74 ===")
print(source)
print("\nDoes the source contain 'subsid'?", "subsid" in source.lower())

question = "Which scheme gives subsidy for solar pump sets?"

tests = {
    "CORRECT answer": (
        "The Chief Minister's Scheme of Solar Powered Pump-set, from the Agricultural "
        "Engineering department, aims to meet farmers' electricity needs for irrigation "
        "and promote solar energy."
    ),
    "WRONG answer (made-up facts)": (
        "The Chief Minister's Scheme of Solar Powered Pump-set gives a 90% subsidy on "
        "5 HP pumps. Applications close on 31 March and farmers must own at least 2 acres."
    ),
}

for label, answer in tests.items():
    r = validate_answer(question, source, answer)
    print(f"\n--- {label} ---")
    print("answers_question:", r.answers_question)
    print("supported:", r.supported)
    print("unsupported_claims:", r.unsupported_claims)