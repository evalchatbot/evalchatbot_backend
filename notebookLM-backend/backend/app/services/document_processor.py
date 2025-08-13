from typing import List, Dict, Optional
import numpy as np
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
import logging
import os
from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self, groq_api_key: str):
        self.llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name="llama3-8b-8192"  # Using Llama3-8B for cost efficiency
        )
        self.embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5") # Initialize FastEmbed model
        self.system_prompt = """You are an intelligent assistant that helps users understand books and documents. 
        You can only answer questions based on the information provided in the context. 
        Always cite your sources by mentioning the book title and page numbers.
        If you don't have enough information to answer a question, say so clearly.
        Be helpful, accurate, and concise in your responses."""
    
    
    
    def _generate_query_embedding(self, query: str) -> np.ndarray:
        """
        Generate embedding for the query using FastEmbed
        """
        try:
            # Generate embedding for the query
            query_embedding = list(self.embedding_model.embed([query]))[0]
            return query_embedding
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            # Fallback to random vector if embedding fails
            return np.random.rand(384)
    
    def create_context_from_chunks(self, chunks: List[Dict]) -> str:
        """
        Create context string from retrieved chunks
        """
        context_parts = []
        
        for chunk in chunks:
            book_title = chunk.get("book_title", "Unknown Book")
            page_start = chunk.get("page_start", "?")
            page_end = chunk.get("page_end", "?")
            
            context_part = f"[From {book_title}, pages {page_start}-{page_end}]\n{chunk['content']}\n"
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    def generate_response(
        self, 
        query: str, 
        context: str, 
        conversation_history: List[Dict] = None
    ) -> Dict:
        """
        Generate response using Groq LLM with context
        """
        try:
            # Build conversation context
            messages = [SystemMessage(content=self.system_prompt)]
            
            # Add conversation history if available
            if conversation_history:
                for msg in conversation_history[-5:]:  # Last 5 messages for context
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    else:
                        messages.append(SystemMessage(content=msg["content"]))
            
            # Add current query with context
            query_with_context = f"""Context information:
{context}

User question: {query}

Please answer based only on the context provided above. Include citations to specific books and page numbers."""
            
            messages.append(HumanMessage(content=query_with_context))
            
            # Generate response
            response = self.llm.invoke(messages)
            
            return {
                "response": response.content,
                "context_used": context,
                "chunks_retrieved": len(context.split("[From")) - 1
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "response": "I apologize, but I encountered an error while processing your request. Please try again.",
                "context_used": "",
                "chunks_retrieved": 0
            }
    
    def update_memory_summary(
        self, 
        current_summary: str, 
        new_conversation: Dict
    ) -> str:
        """
        Update memory summary with new conversation
        """
        try:
            update_prompt = f"""Current summary: {current_summary}

New conversation:
Question: {new_conversation.get('question', '')}
Answer: {new_conversation.get('answer', '')}

Please update the summary to include key points from this new conversation. Keep it concise but comprehensive."""
            
            messages = [
                SystemMessage(content="You are a helpful assistant that creates concise summaries."),
                HumanMessage(content=update_prompt)
            ]
            
            response = self.llm.invoke(messages)
            return response.content
            
        except Exception as e:
            logger.error(f"Error updating memory summary: {e}")
            return current_summary
    
    def extract_key_facts(self, conversation: Dict) -> List[str]:
        """
        Extract key facts from a conversation
        """
        try:
            extract_prompt = f"""From this conversation, extract 3-5 key facts or insights:

Question: {conversation.get('question', '')}
Answer: {conversation.get('answer', '')}

Please list the key facts as bullet points."""
            
            messages = [
                SystemMessage(content="You are a helpful assistant that extracts key facts."),
                HumanMessage(content=extract_prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            # Parse response into list of facts
            facts = [line.strip() for line in response.content.split('\n') if line.strip().startswith('-') or line.strip().startswith('•')]
            return facts[:5]  # Limit to 5 facts
            
        except Exception as e:
            logger.error(f"Error extracting key facts: {e}")
            return []
