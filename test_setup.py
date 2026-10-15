from dotenv import load_dotenv
import faiss, langchain, streamlit, fastapi
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

load_dotenv()
print("Libraries OK. LangChain version:", langchain.__version__)

emb = OpenAIEmbeddings(model="text-embedding-3-small")
vec = emb.embed_query("farmer scheme")
print("Embedding OK. Vector length:", len(vec))

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
print("LLM OK:", llm.invoke("Say hello in one word").content)