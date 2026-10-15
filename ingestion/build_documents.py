from pathlib import Path
import json
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

ROOT = Path(__file__).resolve().parent.parent
SCHEMES_FILE = ROOT / "data" / "schemes.json"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def load_schemes():
    return json.loads(SCHEMES_FILE.read_text(encoding="utf-8"))


def scheme_to_document(s):
    """One scheme -> one Document (body text + metadata)."""
    parts = [
        f"Description: {s['description']}",
        f"Eligibility: {s['eligibility']}",
        f"Documents required: {s['documents_required']}",
    ]
    go = s["go_guidelines"]
    if go and go.lower() != "not uploaded":
        parts.append(f"GO & Guidelines: {go}")

    return Document(
        page_content="\n".join(parts),
        metadata={
            "scheme_id": s["scheme_id"],
            "scheme_name": s["scheme_name"],
            "department": s["department"],
            "s_no": s["s_no"],
        },
    )


def split_documents(docs):
    """Split long documents; put a header on EVERY chunk so context is never lost."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n", ". ", " ", ""],
    )
    chunks = []
    for doc in docs:
        header = (f"Scheme: {doc.metadata['scheme_name']}\n"
                  f"Department: {doc.metadata['department']}\n")
        pieces = splitter.split_text(doc.page_content)
        for i, piece in enumerate(pieces):
            chunks.append(
                Document(
                    page_content=header + piece,
                    metadata={**doc.metadata, "chunk_index": i, "total_chunks": len(pieces)},
                )
            )
    return chunks


def load_chunks():
    """Used by the next step (building the FAISS index)."""
    docs = [scheme_to_document(s) for s in load_schemes()]
    return split_documents(docs)


if __name__ == "__main__":
    schemes = load_schemes()
    docs = [scheme_to_document(s) for s in schemes]
    chunks = split_documents(docs)

    lengths = [len(c.page_content) for c in chunks]
    print("Schemes (Documents):", len(docs))
    print("Chunks after splitting:", len(chunks))
    print(f"Chunk length: min={min(lengths)}, max={max(lengths)}, avg={sum(lengths)//len(lengths)}")

    multi = [c for c in chunks if c.metadata["total_chunks"] > 1 and c.metadata["chunk_index"] == 0]
    print("\nSchemes split into multiple chunks:")
    for c in multi:
        print(f'  - {c.metadata["scheme_name"][:60]} -> {c.metadata["total_chunks"]} chunks')

    print("\n--- Example chunk ---")
    print(chunks[0].page_content)
    print("\nMetadata:", chunks[0].metadata)