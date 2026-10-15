from pathlib import Path
from functools import lru_cache
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

ROOT = Path(__file__).resolve().parent.parent
INDEX_DIR = ROOT / "vectorstore"

load_dotenv(ROOT / ".env")

TOP_K = 5
DISTANCE_THRESHOLD = 1.45  # loose gate; the LLM + validation steps do the final check


@lru_cache(maxsize=1)
def get_vectorstore():
    """Load the saved FAISS index once and reuse it."""
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return FAISS.load_local(
        str(INDEX_DIR), embeddings, allow_dangerous_deserialization=True
    )


def distance_to_relevance(distance):
    """Convert FAISS L2 distance to a 0-100% relevance (vectors are normalized)."""
    return max(0.0, min(100.0, (1 - distance / 2) * 100))


def retrieve(query, k=TOP_K, threshold=DISTANCE_THRESHOLD):
    """Return (kept, rejected): each is a list of dicts with doc, distance, relevance."""
    vs = get_vectorstore()
    results = vs.similarity_search_with_score(query, k=k)

    kept, rejected = [], []
    for doc, distance in results:
        item = {
            "doc": doc,
            "distance": float(distance),
            "relevance": round(distance_to_relevance(float(distance)), 1),
        }
        (kept if distance <= threshold else rejected).append(item)
    return kept, rejected


if __name__ == "__main__":
    import time

    test_queries = [
        "scheme for solar pump sets",
        "help for farmers to sell produce at good price",
        "how to get organic certification",
        "loan or subsidy to start a food processing business",
        "cold storage for vegetables",
        "tractor subsidy",
        "crop insurance",
        "what is the capital of France",
        "cricket score today",
    ]

    for q in test_queries:
        start = time.time()
        kept, rejected = retrieve(q)
        elapsed = time.time() - start
        print(f'\nQuery: "{q}"  ({elapsed:.2f}s)  -> kept {len(kept)}, rejected {len(rejected)}')
        for r in kept:
            print(f'  KEEP   dist={r["distance"]:.3f}  rel={r["relevance"]:>5}%  '
                  f'{r["doc"].metadata["scheme_name"][:55]}')
        for r in rejected[:2]:
            print(f'  reject dist={r["distance"]:.3f}  rel={r["relevance"]:>5}%  '
                  f'{r["doc"].metadata["scheme_name"][:55]}')