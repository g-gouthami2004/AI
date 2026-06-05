"""PDF-aware CLI chatbot using LangChain, Groq, and InMemoryVectorStore."""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.vectorstores import InMemoryVectorStore

load_dotenv()

SYSTEM_PROMPT = "You are a helpful assistant. Answer questions based on PDF content if provided."
MODEL_NAME = "llama-3.3-70b-versatile"
EMBEDDER_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE, CHUNK_OVERLAP, TOP_K = 1000, 100, 3

embedder = HuggingFaceEmbeddings(model_name=EMBEDDER_NAME)
llm = ChatGroq(api_key=os.environ.get("GROQ_API_KEY"), model_name=MODEL_NAME)
history = ChatMessageHistory()
history.add_message(SystemMessage(content=SYSTEM_PROMPT))
vector_store = InMemoryVectorStore(embedding=embedder)

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])

chain = prompt | llm


def load_pdf(path):
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    ).split_documents(PyPDFLoader(path).load())
    if not chunks:
        print("No text found in PDF.")
        return False
    vector_store.add_documents(chunks)
    print(f"PDF loaded: {len(chunks)} chunks.\n")
    return True


def get_input(user_input):
    results = vector_store.similarity_search(user_input, k=TOP_K)
    if not results:
        return user_input
    context = "---".join(d.page_content for d in results)
    return (
        f"PDF context:\n\n{context}\n\n"
        f"Answer ONLY using the context above: {user_input}\n"
        "If not in context, state it is missing."
    )


pdf_loaded = False
print("Chat started. Commands: 'load <file.pdf>' | 'exit'\n")
while True:
    user_input = input("You: ").strip()
    if not user_input:
        continue
    elif user_input.lower() == "exit":
        break
    elif user_input.lower().startswith("load "):
        path = user_input[5:].strip()
        if os.path.exists(path):
            pdf_loaded = load_pdf(path)
        else:
            print(f"File not found: {path}\n")
    else:
        try:
            inp = get_input(user_input) if pdf_loaded else user_input
            reply = chain.invoke({
                "history": history.messages,
                "input": inp,
            }).content
            history.add_message(HumanMessage(content=user_input))
            history.add_message(SystemMessage(content=reply))
            print(f"Assistant: {reply}\n")
        except Exception as exc:
            print(f"API Error: {exc}\n")
