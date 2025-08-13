from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..models.database import ChatRequest, ChatResponse, NotebookCreate
from ..services.chat_service import ChatService
from ..services.rag_service import RAGService
from ..services.supabase_service import SupabaseService
import os

router = APIRouter(prefix="/api", tags=["chat"])

# Dependency injection
def get_chat_service():
    groq_api_key = os.getenv("GROQ_API_KEY")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not all([groq_api_key, supabase_url, supabase_key]):
        raise HTTPException(status_code=500, detail="Missing required environment variables")
    
    rag_service = RAGService(groq_api_key)
    supabase_service = SupabaseService(supabase_url, supabase_key)
    return ChatService(rag_service, supabase_service)

@router.post("/chat", response_model=ChatResponse)
async def chat_with_rag(chat_request: ChatRequest, chat_service: ChatService = Depends(get_chat_service)):
    """
    Chat with the RAG system based on selected books/genres
    """
    try:
        response = await chat_service.process_chat(chat_request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@router.post("/notebooks", response_model=dict)
async def create_notebook(
    notebook_data: NotebookCreate, 
    user_id: str,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Create a new notebook session
    """
    try:
        notebook = await chat_service.create_notebook_session(
            user_id=user_id,
            name=notebook_data.name,
            selected_books=notebook_data.selected_books,
            selected_genres=notebook_data.selected_genres
        )
        
        if not notebook:
            raise HTTPException(status_code=500, detail="Failed to create notebook")
        
        return {"message": "Notebook created successfully", "notebook": notebook}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating notebook: {str(e)}")

@router.get("/notebooks/{notebook_id}")
async def get_notebook_summary(
    notebook_id: str,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Get notebook summary including memory and key facts
    """
    try:
        summary = await chat_service.get_notebook_summary(notebook_id)
        
        if not summary:
            raise HTTPException(status_code=404, detail="Notebook not found")
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting notebook summary: {str(e)}")

@router.get("/notebooks/user/{user_id}")
async def get_user_notebooks(
    user_id: str,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Get all notebooks for a user
    """
    try:
        # This would need to be implemented in the chat service
        # For now, we'll use the supabase service directly
        groq_api_key = os.getenv("GROQ_API_KEY")
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        supabase_service = SupabaseService(supabase_url, supabase_key)
        notebooks = await supabase_service.get_user_notebooks(user_id)
        
        return {"notebooks": notebooks}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user notebooks: {str(e)}")

@router.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "chat-api"}
