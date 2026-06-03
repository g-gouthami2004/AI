import os
import json
from groq import Groq
from pypdf import PdfReader
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
HISTORY_FILE = "chat_history.json"
embedder = SentenceTransformer("all-MiniLM-L6-v2")
pdf_chunks = []
chunk_vectors = []
SIMILARITY_THRESHOLD = 0.4

def load_history():
    return json.load(open(HISTORY_FILE)) if os.path.exists(HISTORY_FILE) else [
        {"role": "system", "content": "You are a helpful assistant. Answer questions based on PDF content if provided."}
    ]

def save_history(history):
    json.dump(history, open(HISTORY_FILE, "w"), indent=2)

def load_pdf(path):
    global pdf_chunks, chunk_vectors  # FIX 1: Allows modification of global variables
    reader = PdfReader(path)
    full_text = "".join(f"\n[Page {i+1}]\n{p.extract_text()}" for i, p in enumerate(reader.pages) if p.extract_text())
    
    if not full_text:
        print("No text found in PDF."); return
    
    
    pdf_chunks = [full_text[i:i+1000] for i in range(0, len(full_text), 900)]
    chunk_vectors = embedder.encode(pdf_chunks)
    print(f"PDF loaded: {len(pdf_chunks)} chunks.\n")



def chat(user_input, history):
    if pdf_chunks:
        query_vector = embedder.encode(user_input, convert_to_tensor=True)
        scores = embedder.similarity(query_vector, chunk_vectors)[0]
        relevant_indices = [
            i for i in range(len(scores)) 
            if float(scores[i]) >= SIMILARITY_THRESHOLD
        ]
        
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:3]
        if not top_indices:
            user_input = "The requested information is not in the PDF. Respond strictly stating you cannot answer based on the document."
        else:
            top = [pdf_chunks[i] for i in top_indices]
            user_input = f"PDF context:\n\n{'---'.join(top)}\n\nAnswer ONLY using the context above: {user_input}\nIf not in context, state it is missing."
    history.append({"role": "user", "content": user_input})
    try:
        reply = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=history).choices[0].message.content
    except Exception as e:
        history.pop(); print(f"API Error: {e}"); return None, history
    history.append({"role": "assistant", "content": reply})
    history = [h for h in history if h["role"] == "system"] + [h for h in history if h["role"] != "system"][-20:]
    save_history(history)
    return reply, history

if __name__ == "__main__":
    history = load_history()
    print("Chat started. Commands: 'load <file.pdf>' | 'clear' | 'exit'\n")
    while True:
        user_input = input("You: ").strip()
        if not user_input: continue
        elif user_input.lower() == "exit": break
        elif user_input.lower() == "clear":
            history = [history[0]]; save_history(history); print("History cleared.\n")
        elif user_input.lower().startswith("load "):
            path = user_input[5:].strip()
            load_pdf(path) if os.path.exists(path) else print(f"File not found: {path}\n")
        else:
            result = chat(user_input, history)
            if result[0]: print(f"Assistant: {result[0]}\n"); history = result[1]