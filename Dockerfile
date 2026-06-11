FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir --no-deps --upgrade pip && \
    pip install --no-cache-dir \
    fastapi uvicorn asyncpg python-dotenv \
    langchain langchain-groq langchain-community \
    langchain-huggingface langchain-text-splitters \
    pypdf sentence-transformers \
    python-multipart

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]