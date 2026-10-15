from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.retriever import get_vectorstore
from backend.rag_chain import answer_question


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at startup: load the FAISS index so the first question is fast
    get_vectorstore()
    print("FAISS index loaded. API ready.")
    yield


app = FastAPI(
    title="TN Agriculture Schemes RAG API",
    description="Answers questions about Tamil Nadu agriculture schemes using a FAISS vector store.",
    lifespan=lifespan,
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500,
                          description="The user's question about agriculture schemes.")


class Source(BaseModel):
    scheme_id: str
    scheme_name: str
    department: str
    relevance: float


class AskResponse(BaseModel):
    status: str                      # answered | no_match | unverified_fallback
    answer: str
    sources: list[Source] = []
    validation: dict | None = None
    stopped_at: str | None = None    # retriever | llm | validator (when no_match)
    seconds: float


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    question = req.question.strip()
    if len(question) < 3:
        raise HTTPException(status_code=400, detail="Question is too short.")
    try:
        result = answer_question(question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while answering: {e}")

    return AskResponse(
        status=result["status"],
        answer=result["answer"],
        sources=result.get("sources", []),
        validation=result.get("validation"),
        stopped_at=result.get("gate"),
        seconds=result["seconds"],
    )