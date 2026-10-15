from pathlib import Path
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


class Grounding(BaseModel):
    answers_question: bool = Field(
        description="True if the ANSWER directly addresses the QUESTION asked."
    )
    supported: bool = Field(
        description="True only if EVERY factual claim in the ANSWER is stated in the SOURCE TEXT."
    )
    unsupported_claims: List[str] = Field(
        description="Claims in the ANSWER that are not found in the SOURCE TEXT. Empty list if none."
    )


JUDGE_PROMPT = """You are a strict fact checker for a question-answering system.

You are given a QUESTION, the SOURCE TEXT (the only allowed evidence) and an ANSWER.

Check the ANSWER claim by claim:
- A claim is SUPPORTED only if the SOURCE TEXT states it or it follows directly from it.
- Claims about money, subsidies, percentages, dates, eligibility and documents must match the SOURCE TEXT exactly.
  Example: if the ANSWER says a scheme "provides a subsidy" but the SOURCE TEXT never mentions a subsidy
  or financial assistance, that claim is UNSUPPORTED.
- Statements such as "not mentioned" are fine and need no support.
- Do not use your own knowledge. If it is not in the SOURCE TEXT, it is unsupported.

Also decide whether the ANSWER actually addresses the QUESTION."""

prompt = ChatPromptTemplate.from_messages([
    ("system", JUDGE_PROMPT),
    ("human", "QUESTION:\n{question}\n\nSOURCE TEXT:\n{source}\n\nANSWER:\n{answer}"),
])

judge = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(Grounding)


def validate_answer(question, source_text, answer):
    """Return a Grounding result."""
    return judge.invoke(prompt.format_messages(
        question=question, source=source_text, answer=answer
    ))