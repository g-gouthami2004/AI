import os
import uuid
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_community.chat_message_histories import ChatMessageHistory

load_dotenv()

SYSTEM_PROMPT = "Answer ONLY from the PDF context. If not found, say it is not in the document."
CHUNK_SIZE, CHUNK_OVERLAP, TOP_K, THRESHOLD = 1000, 200, 3, 0.3

app = FastAPI(title="PDF Chat API")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

llm = ChatGroq(model="llama-3.3-70b-versatile")
embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
state: dict = {"vector_store": None, "history": ChatMessageHistory()}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)) -> dict:
    """Upload PDF, chunk and index it."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF files supported.")
    temp = f"temp_{uuid.uuid4().hex}.pdf"
    with open(temp, "wb") as fh:
        fh.write(await file.read())
    try:
        splits = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
        ).split_documents(PyPDFLoader(temp).load())
        if not splits:
            raise HTTPException(400, "No text found in PDF.")
        state["vector_store"] = InMemoryVectorStore.from_documents(splits, embedder)
        state["history"] = ChatMessageHistory()
        return {"message": f"Indexed {len(splits)} chunks from '{file.filename}'."}
    finally:
        if os.path.exists(temp):
            os.remove(temp)


@app.post("/chat")
async def chat(message: str = Form(...)) -> dict:
    """Chat with the uploaded PDF."""
    if not state["vector_store"]:
        raise HTTPException(400, "Upload a PDF first.")
    results = state["vector_store"].similarity_search_with_score(message, k=TOP_K)
    relevant = [d.page_content for d, s in results if s >= THRESHOLD]
    if not relevant:
        return {"response": "This information is not available in the PDF."}
    context = "\n---\n".join(relevant)
    messages = [
        SystemMessage(content=f"{SYSTEM_PROMPT}\n\nContext:\n{context}"),
        *state["history"].messages,
        HumanMessage(content=message),
    ]
    reply = llm.invoke(messages).content
    state["history"].add_message(HumanMessage(content=message))
    state["history"].add_message(AIMessage(content=reply))
    return {"response": reply}


@app.post("/clear")
async def clear() -> dict:
    """Clear chat history."""
    state["history"] = ChatMessageHistory()
    return {"message": "History cleared."}


@app.get("/history")
async def history() -> dict:
    """Get chat history."""
    return {"history": [
        {"role": "human" if isinstance(m, HumanMessage) else "ai", "content": m.content}
        for m in state["history"].messages
    ]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)