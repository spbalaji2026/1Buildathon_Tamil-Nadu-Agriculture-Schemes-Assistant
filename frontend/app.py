import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="TN Agriculture Schemes Assistant", page_icon="🌾", layout="centered")

EXAMPLES = [
    "Which scheme gives subsidy for solar pump sets?",
    "How can I get organic certification?",
    "Help for farmers to sell produce at a good price",
    "Cold storage for vegetables",
    "Loan or subsidy to start a food processing business",
]


# ---------- helpers ----------
def trigger_search():
    st.session_state.run = True


def set_example(q):
    st.session_state.question_input = q
    st.session_state.run = True


def api_is_up():
    try:
        return requests.get(f"{API_URL}/health", timeout=3).status_code == 200
    except requests.RequestException:
        return False


def ask_api(question):
    return requests.post(f"{API_URL}/ask", json={"question": question}, timeout=90)


# ---------- sidebar ----------
with st.sidebar:
    st.header("About")
    st.write(
        "Answers questions about Tamil Nadu agriculture schemes using a **FAISS vector "
        "database** built from the TN Agrisnet website. No website is contacted while you search."
    )
    st.markdown("**Pipeline**")
    st.markdown(
        "1. Retriever with similarity threshold\n"
        "2. LLM answers from retrieved text only\n"
        "3. Independent validation of the answer"
    )
    st.divider()
    if api_is_up():
        st.success("Backend API: connected")
    else:
        st.error("Backend API: not reachable")
        st.caption("Start it with: py -m uvicorn backend.main:app")

# ---------- main page ----------
st.title("🌾 Tamil Nadu Agriculture Schemes Assistant")
st.caption("Ask about schemes, eligibility and documents required.")

question = st.text_input(
    "Your question",
    key="question_input",
    placeholder="e.g. Which scheme helps with cold storage?",
    on_change=trigger_search,
)
search_clicked = st.button("Search", type="primary")

st.write("Try an example:")
for ex in EXAMPLES:
    st.button(ex, key=f"ex_{ex}", on_click=set_example, args=(ex,))

run = st.session_state.pop("run", False)

if search_clicked or run:
    q = (st.session_state.get("question_input") or "").strip()
    if len(q) < 3:
        st.warning("Please type a question (at least 3 characters).")
    else:
        try:
            with st.spinner("Searching the scheme database..."):
                resp = ask_api(q)
        except requests.ConnectionError:
            st.error("Cannot reach the backend. Start it in another terminal with:\n\n"
                     "`py -m uvicorn backend.main:app`")
            st.stop()
        except requests.Timeout:
            st.error("The request timed out. Please try again.")
            st.stop()

        if resp.status_code != 200:
            st.error(f"The API returned an error (HTTP {resp.status_code}).")
            st.code(resp.text[:500])
            st.stop()

        data = resp.json()
        status = data["status"]

        st.subheader("Answer")
        if status == "answered":
            st.success("Answer verified against the scheme data")
            st.markdown(data["answer"])
        elif status == "unverified_fallback":
            st.warning("Some generated details could not be verified, "
                       "so the original scheme text is shown instead.")
            st.markdown(data["answer"])
        else:
            st.info(data["answer"])

        if data.get("sources"):
            st.subheader("Sources")
            for s in data["sources"]:
                st.markdown(
                    f"- **{s['scheme_name']}**  \n"
                    f"  Department: {s['department']} · Scheme ID: {s['scheme_id']} · "
                    f"Match strength: {s['relevance']}%"
                )

        with st.expander("How this answer was checked"):
            if status == "no_match":
                st.write(f"Stopped at the **{data.get('stopped_at')}** stage; "
                         "no answer was generated.")
            v = data.get("validation")
            if v:
                st.write("Answers the question:", "✅" if v["answers_question"] else "❌")
                st.write("All claims supported by source text:", "✅" if v["supported"] else "❌")
                if v["unsupported_claims"]:
                    st.write("Unsupported claims found:")
                    for c in v["unsupported_claims"]:
                        st.markdown(f"- {c}")
            st.caption(f"Response time: {data['seconds']} seconds")