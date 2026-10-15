# 🌾 Tamil Nadu Agriculture Schemes Assistant (RAG)

A question-answering app for Tamil Nadu agriculture schemes. Ask a question in plain English, and the app finds the matching schemes in a **FAISS vector database**, writes an answer using only that retrieved text, and **validates the answer** before showing it.

**Important:** the scheme data was collected once from the TN Agrisnet website and stored in a local vector database that is included in this repository. **Running the app never contacts the website**, so answers come back in a few seconds.

- Data source: https://www.tnagrisnet.tn.gov.in/people_app/GoScheme (collected October 2026)
- Stack: Python, LangChain, OpenAI, FAISS, FastAPI, Streamlit

---

## How it works

```
Streamlit UI  ──►  FastAPI  /ask  ──►  Retriever (FAISS + threshold)
                                              │
                          nothing close enough? ──► "No matching scheme" (no LLM call)
                                              │
                                              ▼
                                  LLM answers from retrieved text only
                                              │
                          not answerable? ──► "No matching scheme"
                                              │
                                              ▼
                              Validator checks every claim against the source
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
               verified answer         not answering the         unsupported claims →
                                       question → no match       show original scheme text
```

### The three gates

| Gate | Where | What it does |
|---|---|---|
| 1. Similarity threshold | `backend/retriever.py` | Drops chunks whose FAISS distance is above `1.45`. Clearly unrelated questions (for example "capital of France") stop here and the LLM is never called. |
| 2. Answerability check | `backend/rag_chain.py` | The LLM must set `answerable=true` only if a retrieved scheme directly answers the question. Being in the same general topic is not enough. |
| 3. Grounding validation | `backend/validator.py` | A second, independent LLM call checks every claim in the answer against the source text. If any claim is unsupported, the original stored scheme text is shown instead of the generated answer. |

The pipeline is: **Data loading → Text splitting → Embedding → Vector DB → Retrieval → LLM → Validation → Output**.

---

## Project structure

```
tn-scheme-rag/
├── data/
│   └── schemes.json            # Cleaned scheme data (29 schemes)
├── vectorstore/
│   ├── index.faiss             # FAISS vectors (prebuilt, included in the repo)
│   └── index.pkl               # Chunk text + metadata
├── ingestion/                  # One-time data collection (NOT needed to run the app)
│   ├── scrape_schemes.py       # Fetches schemes from the website, cleans, removes duplicates
│   ├── build_documents.py      # Scheme -> LangChain Document -> text chunks
│   ├── build_index.py          # Embeds chunks and saves the FAISS index
│   ├── inspect_page.py         # Helper used to inspect the website
│   ├── find_data_source.py     # Helper used to find the site's data endpoint
│   ├── show_datatable_code.py  # Helper used to read the site's table code
│   └── test_api.py             # Helper used to test the site's data endpoint
├── backend/
│   ├── main.py                 # FastAPI app (/health, /ask)
│   ├── retriever.py            # FAISS retriever with similarity threshold
│   ├── rag_chain.py            # Retrieval + LLM + validation pipeline
│   ├── validator.py            # Answer grounding check
│   ├── test_validator.py       # Proves the validator rejects made-up claims
│   └── test_api_call.py        # Calls the running API from Python
├── frontend/
│   └── app.py                  # Streamlit UI
├── test_setup.py               # Checks libraries and API key
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick start (for running the project)

### 1. Requirements

- Python 3.10 or higher
- An **OpenAI API key**. It is needed to embed your question and to generate and validate answers. For this project, a few questions cost a tiny fraction of a rupee.

### 2. Clone and create a virtual environment

```bash
git clone <your-repo-url>
cd tn-scheme-rag

python -m venv venv

# Windows
venv\Scripts\activate
# Mac / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your OpenAI key

Copy `.env.example` to a new file named `.env` and put your key in it:

```
OPENAI_API_KEY=sk-your-key-here
```

The `.env` file is ignored by git and must never be uploaded.

### 5. (Optional) Check the setup

```bash
python test_setup.py
```

You should see the library check, `Vector length: 1536`, and a short greeting from the LLM.

### 6. Start the backend (Terminal 1)

```bash
python -m uvicorn backend.main:app
```

Wait for `FAISS index loaded. API ready.` and `Application startup complete.`

### 7. Start the frontend (Terminal 2)

Open a second terminal in the project folder, activate the virtual environment again, then:

```bash
python -m streamlit run frontend/app.py
```

The app opens at **http://localhost:8501**. The sidebar should show **Backend API: connected**.

> On Windows you can use `py` instead of `python` in all commands.

---

## Example questions to try

| Question | Expected behaviour |
|---|---|
| Which scheme gives subsidy for solar pump sets? | Answered, sourced to the Solar Powered Pump-set scheme |
| How can I get organic certification and what documents do I need? | Answered, with the NPOP document list |
| Help for farmers to sell produce at a good price | Answered from the marketing schemes |
| Crop insurance | "No matching scheme" (no such scheme in the data; stopped by the LLM gate) |
| What is the capital of France? | "No matching scheme" (stopped by the retriever; no LLM call) |

The **"How this answer was checked"** box under each answer shows which stage handled the question and the validation result.

### Testing the API directly

With the backend running, open **http://127.0.0.1:8000/docs**, click **POST /ask → Try it out**, and enter:

```json
{"question": "How can I get organic certification?"}
```

### Testing the validator

```bash
python backend/test_validator.py
```

This feeds the validator one correct answer and one answer with invented facts. The correct one passes and the invented one is rejected with each unsupported claim listed.

---

## Design decisions

- **Two phases.** Data collection (`ingestion/`) runs once and needs internet. The app only reads the saved index. That is why the FAISS files are committed to the repository.
- **Data cleaning.** The website returned 52 rows. 23 of them were test entries named "tester" (one with no department), which were removed, leaving **29 real schemes**. Schemes with similar names (for example several TNIAMP entries from different departments or years) were reviewed and kept, because their content differs. Each answer shows the department and scheme ID so these can be told apart.
- **Chunking.** One document per scheme, split at 800 characters with 100 overlap. Every chunk starts with the scheme name and department, so no chunk loses its context. 29 schemes became 44 chunks.
- **Embeddings.** OpenAI `text-embedding-3-small` (1536 dimensions). The question must be embedded with the same model that built the index, which is why an API key is needed at query time.
- **Why the threshold is 1.45.** FAISS returns a distance (lower is closer). On this data, good matches scored about 0.74 to 0.94, loose matches 1.0 to 1.45, and unrelated questions 1.67 to 1.84. A strict cutoff of 1.2 wrongly rejected valid short queries such as "tractor subsidy", and no single number can separate every case. So the threshold is a loose first filter and the LLM and validator make the final decision.
- **LLM.** `gpt-4o-mini` with `temperature=0`, so the same question gives the same answer.
- **Safe fallback.** If the validator finds an unsupported claim, the app shows the stored scheme text instead of the generated answer.

---

## Rebuilding the data (optional)

Only needed if the website data changes. This requires internet and your OpenAI key.

```bash
python ingestion/scrape_schemes.py     # fetch, clean, remove duplicates -> data/schemes.json
python ingestion/build_documents.py    # preview the chunks (optional)
python ingestion/build_index.py        # embed and save the FAISS index -> vectorstore/
```

The scraper makes only three polite requests (25 rows each, with a one-second pause) to the website's public table endpoint.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Sidebar says **Backend API: not reachable** | Start the backend first (step 6) and check it is on port 8000. |
| `AuthenticationError` or `OPENAI_API_KEY` not found | Check that `.env` exists in the project root and contains your key. Restart the backend after editing `.env`. |
| `ModuleNotFoundError: backend` | Run commands from the project root folder, not from inside `backend/`. |
| Quota or billing error from OpenAI | Check that your OpenAI account has credit. |
| `DeprecationWarning` about `langchain-community` | Harmless. It is a packaging notice from LangChain and does not affect the app. |
| Browser shows "Not Found" at `http://127.0.0.1:8000/` | Use `/docs` (for example `http://127.0.0.1:8000/docs`). |

---

## Notes and limitations

- The database holds **29 schemes** as published on the website in October 2026. Newer or changed schemes are not included until the data is rebuilt.
- Some source records are short or incomplete (for example, a description that only repeats the scheme name, or "Documents required" left empty). The app reports such details as "not mentioned" rather than guessing.
- A question must match the wording of the scheme data reasonably well. For example, "tractor subsidy" does not match "farm mechanization" strongly enough, and the app correctly says it found no matching scheme.
- `index.pkl` is loaded with `allow_dangerous_deserialization=True`, which LangChain requires for pickle files. This is safe here because the file was created by this project. Do not load index files from sources you do not trust.
- Answers are generated from the stored data and are for information only. Confirm eligibility and documents with the relevant department before applying.
