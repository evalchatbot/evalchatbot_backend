from typing import List, Dict, Optional
import logging
from .rag_service import RAGService
from .supabase_service import SupabaseService
from ..models.database import ChatRequest, ChatResponse, Notebook

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, rag_service: RAGService, supabase_service: SupabaseService):
        self.rag_service = rag_service
        self.supabase_service = supabase_service
    
    async def process_chat(self, chat_request: ChatRequest) -> ChatResponse:
        """
        Main chat processing pipeline
        """
        try:
            # Get notebook details
            notebook = await self.supabase_service.get_notebook_by_id(chat_request.notebook_id, chat_request.user_id)
            if not notebook:
                raise ValueError(f"Notebook {chat_request.notebook_id} not found")
            
            book_ids = notebook.get("selected_books", [])
            genres = notebook.get("selected_genres", [])

            # If no specific books selected but genres are, get book IDs by genre
            if not book_ids and genres:
                for genre in genres:
                    genre_books = await self.supabase_service.get_books_by_genre(genre)
                    book_ids.extend([book["id"] for book in genre_books])
                book_ids = list(set(book_ids)) # Remove duplicates

            if not book_ids:
                return ChatResponse(
                    response="I don't have access to any documents in this notebook. Please select some books or genres first.",
                    citations=[],
                    memory_summary=notebook.get("memory_summary", ""),
                    key_facts=notebook.get("key_facts", [])
                )

            # Generate query embedding
            query_embedding = self.rag_service._generate_query_embedding(chat_request.message)

            # Search for relevant chunks using Supabase vector search
            relevant_chunks = await self.supabase_service.search_chunks_vector(
                query_embedding.tolist(), # Convert numpy array to list for Supabase
                book_ids,
                top_k=5
            )
            
            # Add book titles to chunks for better context (optimized)
            if relevant_chunks:
                unique_book_ids = list(set(chunk["book_id"] for chunk in relevant_chunks))
                books_data = await self.supabase_service.get_books_by_ids(unique_book_ids)
                book_map = {book["id"]: book for book in books_data}

                for chunk in relevant_chunks:
                    book = book_map.get(chunk["book_id"])
                    if book:
                        chunk["book_title"] = book["title"]
                        chunk["book_author"] = book["author"]

            if not relevant_chunks:
                return ChatResponse(
                    response="I couldn't find any relevant information in the selected documents to answer your question. Please try rephrasing or ask about a different topic.",
                    citations=[],
                    memory_summary=notebook.get("memory_summary", ""),
                    key_facts=notebook.get("key_facts", [])
                )
            
            # Create context from chunks
            context = self.rag_service.create_context_from_chunks(relevant_chunks)
            
            # Get chat history for context
            chat_history = await self.supabase_service.get_chat_history(chat_request.notebook_id, limit=10)
            
            # Generate response
            rag_response = self.rag_service.generate_response(
                chat_request.message,
                context,
                self._format_chat_history(chat_history)
            )
            
            # Extract citations from chunks
            citations = self._extract_citations(relevant_chunks)
            
            # Update notebook memory
            new_memory_summary = await self._update_notebook_memory(
                notebook, 
                chat_request.message, 
                rag_response["response"]
            )
            
            # Extract key facts
            new_key_facts = self.rag_service.extract_key_facts({
                "question": chat_request.message,
                "answer": rag_response["response"]
            })
            
            # Save chat message
            await self.supabase_service.save_chat_message({
                "notebook_id": chat_request.notebook_id,
                "user_message": chat_request.message,
                "assistant_response": rag_response["response"],
                "citations": citations
            })
            
            # Update notebook with new memory and facts
            await self.supabase_service.update_notebook_memory(
                chat_request.notebook_id,
                new_memory_summary,
                new_key_facts
            )
            
            return ChatResponse(
                response=rag_response["response"],
                citations=citations,
                memory_summary=new_memory_summary,
                key_facts=new_key_facts
            )
            
        except Exception as e:
            logger.error(f"Error processing chat: {e}")
            return ChatResponse(
                response="I apologize, but I encountered an error while processing your request. Please try again.",
                citations=[],
                memory_summary="",
                key_facts=[]
            )
    
    
    
    def _format_chat_history(self, chat_history: List[Dict]) -> List[Dict]:
        """
        Format chat history for the LLM
        """
        formatted_history = []
        for msg in chat_history:
            formatted_history.append({
                "role": "user",
                "content": msg["user_message"]
            })
            formatted_history.append({
                "role": "assistant", 
                "content": msg["assistant_response"]
            })
        return formatted_history
    
    def _extract_citations(self, chunks: List[Dict]) -> List[Dict]:
        """
        Extract citation information from chunks
        """
        citations = []
        for chunk in chunks:
            citation = {
                "book_title": chunk.get("book_title", "Unknown Book"),
                "book_author": chunk.get("book_author", "Unknown Author"),
                "page_start": chunk.get("page_start", "?"),
                "page_end": chunk.get("page_end", "?"),
                "content_preview": chunk["content"][:100] + "..." if len(chunk["content"]) > 100 else chunk["content"]
            }
            citations.append(citation)
        return citations
    
    async def _update_notebook_memory(
        self, 
        notebook: Dict, 
        question: str, 
        answer: str
    ) -> str:
        """
        Update notebook memory with new conversation
        """
        try:
            current_summary = notebook.get("memory_summary", "")
            
            new_memory = self.rag_service.update_memory_summary(
                current_summary,
                {"question": question, "answer": answer}
            )
            
            return new_memory
            
        except Exception as e:
            logger.error(f"Error updating notebook memory: {e}")
            return notebook.get("memory_summary", "")
    
    async def create_notebook_session(
        self, 
        user_id: str, 
        name: str, 
        selected_books: List[str] = None, 
        selected_genres: List[str] = None
    ) -> Optional[Dict]:
        """
        Create a new notebook session
        """
        try:
            notebook_data = {
                "user_id": user_id,
                "name": name,
                "selected_books": selected_books or [],
                "selected_genres": selected_genres or []
            }
            
            notebook = await self.supabase_service.create_notebook(notebook_data)
            return notebook
            
        except Exception as e:
            logger.error(f"Error creating notebook session: {e}")
            return None
    
    async def get_notebook_summary(self, notebook_id: str) -> Optional[Dict]:
        """
        Get notebook summary including memory and key facts
        """
        try:
            notebook = await self.supabase_service.get_notebook_by_id(notebook_id)
            if not notebook:
                return None
            
            return {
                "id": notebook["id"],
                "name": notebook["name"],
                "memory_summary": notebook.get("memory_summary", ""),
                "key_facts": notebook.get("key_facts", []),
                "selected_books": notebook.get("selected_books", []),
                "selected_genres": notebook.get("selected_genres", []),
                "created_at": notebook["created_at"],
                "updated_at": notebook["updated_at"]
            }
            
        except Exception as e:
            logger.error(f"Error getting notebook summary: {e}")
            return None
