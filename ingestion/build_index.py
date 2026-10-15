from pathlib import Path
import time
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from build_documents import load_chunks

ROOT = Path(__file__).resolve().parent.parent
INDEX_DIR = ROOT / "vectorstore"
INDEX_DIR.mkdir(exist_ok=True)

load_dotenv(ROOT / ".env")


def main():
    chunks = load_chunks()
    print("Chunks to embed:", len(chunks))

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    start = time.time()
    vectorstore = FAISS.from_documents(chunks, embeddings)
    print(f"Embedded and indexed in {time.time() - start:.1f} seconds")

    vectorstore.save_local(str(INDEX_DIR))
    print("Saved index to:", INDEX_DIR)
    print("Files:", [p.name for p in INDEX_DIR.iterdir()])

    # ---- Quick sanity test: reload from disk and search ----
    print("\n--- Sanity test (loading from disk) ---")
    start = time.time()
    loaded = FAISS.load_local(
        str(INDEX_DIR), embeddings, allow_dangerous_deserialization=True
    )
    print(f"Loaded in {time.time() - start:.2f} seconds")

    queries = [
        "scheme for solar pump sets",
        "help for farmers to sell produce at good price",
        "how to get organic certification",
        "what is the capital of France",   # irrelevant on purpose
    ]
    for q in queries:
        start = time.time()
        results = loaded.similarity_search_with_score(q, k=3)
        print(f'\nQuery: "{q}"  ({time.time() - start:.2f}s)')
        for doc, score in results:
            print(f'  score={score:.3f}  {doc.metadata["scheme_name"][:60]}')


if __name__ == "__main__":
    main()