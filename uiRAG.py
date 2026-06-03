import os
import streamlit as st
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore 
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


load_dotenv()

client = ChatGroq(
    model="llama-3.3-70b-versatile",
    groq_api_key=os.environ.get("GROQ_API_KEY")
)

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def process_pdf_with_langchain(file):
    temp_path = f"temp_{file.name}"
    with open(temp_path, "wb") as f:
        f.write(file.getvalue())
    
    try:
        loader = PyPDFLoader(temp_path)
        docs = loader.load()
        

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        split_docs = text_splitter.split_documents(docs)
        if not split_docs:
            return None
        
        vector_store = InMemoryVectorStore.from_documents(split_docs, embeddings)
        return vector_store
        
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


st.set_page_config(page_title="PDF Chat", layout="wide")
st.title("ASK US")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        SystemMessage(content="You are a helpful assistant. Answer questions based on PDF content if provided.")
    ]

if "vector_store" not in st.session_state:
    st.session_state.vector_store = None

with st.sidebar:
    st.header("Upload PDF")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file:
        with st.spinner("Loading pdf..."):
            vector_store = process_pdf_with_langchain(uploaded_file)
        if vector_store:
            st.session_state.vector_store = vector_store
            st.success("PDF loaded successfully.")
        else :
            st.session_state.vector_store = None
            st.error("No text found in this PDF.")
    if st.button("Clear History"):
        st.session_state.chat_history = [st.session_state.chat_history[0]]

        st.success("History cleared.")

for msg in st.session_state.chat_history:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(msg.content)
    elif isinstance(msg, AIMessage):
        with st.chat_message("assistant"):
            st.markdown(msg.content)

if prompt := st.chat_input("Ask something about your PDF..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
             if st.session_state.vector_store:
                docs = st.session_state.vector_store.similarity_search(prompt, k=3)
                
                context = "\n\n".join(doc.page_content for doc in docs)
                
                system_instruction = SystemMessage(
                    content=f"Answer the user's question using ONLY the following context:\n\n{context}"
                )
                
                current_messages = [system_instruction] + st.session_state.chat_history + [HumanMessage(content=prompt)]
                
                reply = client.invoke(current_messages).content
            
             else:
                current_messages = st.session_state.chat_history + [HumanMessage(content=prompt)]
                reply = client.invoke(current_messages).content
            
            st.markdown(reply)
            
            st.session_state.chat_history.append(HumanMessage(content=prompt))
            st.session_state.chat_history.append(AIMessage(content=reply))
