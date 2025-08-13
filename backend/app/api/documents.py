from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List
import os
import shutil
from ..models.database import DocumentIngestRequest
from ..services.document_processor import DocumentProcessor
from ..services.supabase_service import SupabaseService
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Dependency injection
def get_document_processor():
    return DocumentProcessor()

def get_supabase_service():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Use service role for admin operations
    
    if not all([supabase_url, supabase_key]):
        raise HTTPException(status_code=500, detail="Missing required environment variables")
    
    return SupabaseService(supabase_url, supabase_key)

@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    title: str = None,
    author: str = None,
    genre: str = None,
    document_processor: DocumentProcessor = Depends(get_document_processor),
    supabase_service: SupabaseService = Depends(get_supabase_service)
):
    """
    Ingest a PDF document into the system
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Create upload directory if it doesn't exist
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save uploaded file
        file_path = os.path.join(upload_dir, f"{uuid.uuid4()}_{file.filename}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process document
        chunks = document_processor.process_document(file_path)
        
        if not chunks:
            raise HTTPException(status_code=500, detail="Failed to process document")
        
        # Create book record
        book_data = {
            "title": title or file.filename.replace('.pdf', ''),
            "author": author or "Unknown Author",
            "genre": genre or "other",
            "file_path": file_path,
            "total_pages": max(chunk["page_end"] for chunk in chunks) if chunks else 0
        }
        
        book = await supabase_service.create_book(book_data)
        
        if not book:
            raise HTTPException(status_code=500, detail="Failed to create book record")
        
        # Add book_id to chunks
        for chunk in chunks:
            chunk["book_id"] = book["id"]
        
        # Store chunks in database
        stored_chunks = await supabase_service.create_chunks(chunks)
        
        if not stored_chunks:
            raise HTTPException(status_code=500, detail="Failed to store document chunks")
        
        return {
            "message": "Document ingested successfully",
            "book": book,
            "chunks_created": len(stored_chunks),
            "total_pages": book_data["total_pages"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ingesting document: {str(e)}")
    finally:
        # Clean up uploaded file
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

@router.post("/ingest-batch")
async def ingest_batch_documents(
    documents: List[DocumentIngestRequest],
    document_processor: DocumentProcessor = Depends(get_document_processor),
    supabase_service: SupabaseService = Depends(get_supabase_service)
):
    """
    Ingest multiple documents from file paths (for admin use)
    """
    try:
        results = []
        
        for doc_request in documents:
            try:
                # Check if file exists
                if not os.path.exists(doc_request.file_path):
                    results.append({
                        "file_path": doc_request.file_path,
                        "status": "error",
                        "message": "File not found"
                    })
                    continue
                
                # Process document
                chunks = document_processor.process_document(doc_request.file_path)
                
                if not chunks:
                    results.append({
                        "file_path": doc_request.file_path,
                        "status": "error",
                        "message": "Failed to process document"
                    })
                    continue
                
                # Create book record
                book_data = {
                    "title": doc_request.title,
                    "author": doc_request.author,
                    "genre": doc_request.genre,
                    "file_path": doc_request.file_path,
                    "total_pages": max(chunk["page_end"] for chunk in chunks) if chunks else 0
                }
                
                book = await supabase_service.create_book(book_data)
                
                if not book:
                    results.append({
                        "file_path": doc_request.file_path,
                        "status": "error",
                        "message": "Failed to create book record"
                    })
                    continue
                
                # Add book_id to chunks
                for chunk in chunks:
                    chunk["book_id"] = book["id"]
                
                # Store chunks in database
                stored_chunks = await supabase_service.create_chunks(chunks)
                
                results.append({
                    "file_path": doc_request.file_path,
                    "status": "success",
                    "book_id": book["id"],
                    "chunks_created": len(stored_chunks),
                    "total_pages": book_data["total_pages"]
                })
                
            except Exception as e:
                results.append({
                    "file_path": doc_request.file_path,
                    "status": "error",
                    "message": str(e)
                })
        
        return {
            "message": "Batch ingestion completed",
            "results": results,
            "total_processed": len(documents),
            "successful": len([r for r in results if r["status"] == "success"]),
            "failed": len([r for r in results if r["status"] == "error"])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in batch ingestion: {str(e)}")

@router.get("/books")
async def get_all_books(supabase_service: SupabaseService = Depends(get_supabase_service)):
    """
    Get all books in the system
    """
    try:
        # This would need to be implemented in the supabase service
        # For now, we'll return a placeholder
        return {"message": "Get all books endpoint - to be implemented"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting books: {str(e)}")

@router.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "document-api"}
