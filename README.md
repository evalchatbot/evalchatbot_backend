# Inside LM - RAG-based Book Analysis Platform

A RAG (Retrieval-Augmented Generation) system for analyzing books and providing intelligent chat-based insights.

## Project Structure

```
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── models/         # Pydantic models
│   │   ├── services/       # Business logic
│   │   ├── api/            # API endpoints
│   │   └── main.py         # FastAPI app
├── data_ingestion/         # Document processing pipeline
├── requirements.txt         # Python dependencies
└── .env.example            # Environment variables template
```

## Features

- PDF document ingestion with OCR support
- Chunk-level text splitting (800-1000 chars, 100 overlap)
- FastEmbed vector embeddings
- Groq LLM integration
- Per-notebook memory with running summary
- Chunk-level citations (book title + page numbers)
- Supabase integration for data storage

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in your credentials
3. Run the backend: `cd backend && uvicorn app.main:app --reload`
4. Run data ingestion: `python data_ingestion/main.py`

## API Endpoints

- `POST /chat` - Chat with the RAG system
- `POST /notebooks` - Create new notebook session
- `GET /notebooks/{id}` - Get notebook details
- `POST /documents/ingest` - Ingest new documents
