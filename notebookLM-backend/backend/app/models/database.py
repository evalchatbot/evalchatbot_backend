from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class Genre(str, Enum):
    HISTORY = "history"
    SCIENCE = "science"
    LITERATURE = "literature"
    PHILOSOPHY = "philosophy"
    TECHNOLOGY = "technology"
    OTHER = "other"

class Book(BaseModel):
    id: str
    title: str
    author: str
    genre: Genre
    file_path: str
    total_pages: int
    created_at: datetime
    updated_at: datetime

class DocumentChunk(BaseModel):
    id: str
    book_id: str
    content: str
    page_start: int
    page_end: int
    chunk_index: int
    embedding: List[float]
    metadata: dict
    created_at: datetime

class Notebook(BaseModel):
    id: str
    user_id: str
    name: str
    selected_books: List[str]  # List of book IDs
    selected_genres: List[Genre]
    memory_summary: str
    key_facts: List[str]
    created_at: datetime
    updated_at: datetime

class ChatMessage(BaseModel):
    id: str
    notebook_id: str
    user_message: str
    assistant_response: str
    citations: List[dict]  # List of chunk citations
    timestamp: datetime

class ChatRequest(BaseModel):
    notebook_id: str
    message: str
    user_id: str

class ChatResponse(BaseModel):
    response: str
    citations: List[dict]
    memory_summary: str
    key_facts: List[str]

class NotebookCreate(BaseModel):
    name: str
    selected_books: List[str] = []
    selected_genres: List[Genre] = []

class DocumentIngestRequest(BaseModel):
    file_path: str
    title: str
    author: str
    genre: Genre
