from pathlib import Path
from collections import OrderedDict
import time
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

try:
    from backend.retriever import retrieve
    from backend.validator import validate_answer
except ImportError:          # when run directly: py backend\rag_chain.py
    from retriever import retrieve
    from validator import validate_answer

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

NO_MATCH_MESSAGE = ("I couldn't find a scheme in the database that matches your question. "
                    "Try rephrasing it, for example with the crop, activity or type of help you need.")


class LLMAnswer(BaseModel):
    answerable: bool = Field(
        description="True ONLY if at least one provided scheme directly answers the question."
    )
    answer: str = Field(
        description="Clear answer based only on the provided schemes. "
                    "If answerable is false, a short explanation that no provided scheme matches."
    )
    used_scheme_ids: List[str] = Field(
        description="scheme_id values of the schemes the answer is based on. Empty if not answerable."
    )


SYSTEM_PROMPT = """You are an assistant that answers questions about Tamil Nadu agriculture schemes.

STRICT RULES:
1. Use ONLY the scheme information in the CONTEXT below. Never use outside knowledge.
2. Set answerable=true ONLY if at least one scheme in the context directly addresses what the user asked.
   Being in the same general area (for example, farming) is NOT enough.
   Example: a question about crop insurance is NOT answered by a price support scheme.
3. If no scheme directly matches, set answerable=false, used_scheme_ids=[], and say briefly that
   no matching scheme was found. Do not guess and do not suggest unrelated schemes as answers.
4. When answerable, name each relevant scheme and its department, and state its purpose,
   eligibility and documents required, but only if these appear in the context.
   If a detail is missing from the context, say it is not mentioned.
5. Put in used_scheme_ids only the scheme_id values of schemes you actually used.
6. Be concise and use simple language."""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "CONTEXT:\n{context}\n\nQUESTION: {question}"),
])

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
structured_llm = llm.with_structured_output(LLMAnswer)


def group_by_scheme(items):
    """Merge chunks of the same scheme, keeping the best (lowest) distance per scheme."""
    grouped = OrderedDict()
    for it in items:
        sid = it["doc"].metadata["scheme_id"]
        g = grouped.setdefault(sid, {"meta": it["doc"].metadata, "chunks": [],
                                     "distance": it["distance"], "relevance": it["relevance"]})
        g["chunks"].append((it["doc"].metadata["chunk_index"], it["doc"].page_content))
        if it["distance"] < g["distance"]:
            g["distance"], g["relevance"] = it["distance"], it["relevance"]
    for g in grouped.values():
        g["chunks"].sort(key=lambda c: c[0])
    return grouped


def build_context(grouped):
    blocks = []
    for sid, g in grouped.items():
        text = "\n".join(c[1] for c in g["chunks"])
        blocks.append(f"[scheme_id: {sid}]\n{text}")
    return "\n\n---\n\n".join(blocks)


def extractive_fallback(grouped, ids):
    """Show the stored scheme text directly (no generated wording)."""
    parts = []
    for sid in ids:
        g = grouped[sid]
        parts.append("\n".join(c[1] for c in g["chunks"]))
    return "\n\n---\n\n".join(parts)


def answer_question(question):
    t0 = time.time()
    kept, rejected = retrieve(question)

    # Gate 1: nothing close enough -> no LLM call
    if not kept:
        return {"status": "no_match", "answer": NO_MATCH_MESSAGE, "sources": [],
                "gate": "retriever", "seconds": round(time.time() - t0, 2)}

    grouped = group_by_scheme(kept)
    context = build_context(grouped)

    # Gate 2: the LLM decides if any scheme really answers the question
    result = structured_llm.invoke(prompt.format_messages(context=context, question=question))

    valid_ids = [sid for sid in result.used_scheme_ids if sid in grouped]
    if not result.answerable or not valid_ids:
        return {"status": "no_match", "answer": NO_MATCH_MESSAGE, "sources": [],
                "gate": "llm", "llm_said": result.answer,
                "seconds": round(time.time() - t0, 2)}

    sources = [{"scheme_id": sid, "scheme_name": grouped[sid]["meta"]["scheme_name"],
                "department": grouped[sid]["meta"]["department"],
                "relevance": grouped[sid]["relevance"]} for sid in valid_ids]

    # Gate 3: independent validation against only the schemes the answer used
    used_grouped = {sid: grouped[sid] for sid in valid_ids}
    source_text = build_context(used_grouped)
    check = validate_answer(question, source_text, result.answer)
    validation = {"answers_question": check.answers_question,
                  "supported": check.supported,
                  "unsupported_claims": check.unsupported_claims}

    if not check.answers_question:
        return {"status": "no_match", "answer": NO_MATCH_MESSAGE, "sources": [],
                "gate": "validator", "validation": validation,
                "seconds": round(time.time() - t0, 2)}

    if not check.supported:
        return {"status": "unverified_fallback",
                "answer": ("The generated answer contained details I could not verify, so here is "
                           "the original scheme information from the database:\n\n"
                           + extractive_fallback(grouped, valid_ids)),
                "sources": sources, "validation": validation,
                "seconds": round(time.time() - t0, 2)}

    return {"status": "answered", "answer": result.answer, "sources": sources,
            "validation": validation, "context": context,
            "seconds": round(time.time() - t0, 2)}


if __name__ == "__main__":
    tests = [
        "Which scheme gives subsidy for solar pump sets?",
        "How can I get organic certification and what documents do I need?",
        "tractor subsidy",
        "crop insurance",
        "what is the capital of France",
    ]
    for q in tests:
        r = answer_question(q)
        print("\n" + "=" * 70)
        print("Q:", q)
        gate = f'  [stopped at: {r["gate"]}]' if "gate" in r else ""
        print(f'Status: {r["status"]}   ({r["seconds"]}s){gate}')
        print("A:", r["answer"])
        if r.get("validation"):
            print("Validation:", r["validation"])
        for s in r["sources"]:
            print(f'   source: {s["scheme_name"]} [{s["department"]}] id={s["scheme_id"]}')