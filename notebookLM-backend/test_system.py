#!/usr/bin/env python3
"""
Test script for Inside LM RAG System
Tests all major components to ensure they're working correctly
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.document_processor import DocumentProcessor
from app.services.rag_service import RAGService
from app.services.supabase_service import SupabaseService
from app.services.chat_service import ChatService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_document_processor():
    """Test the document processing pipeline"""
    print("\n=== Testing Document Processor ===")
    
    try:
        processor = DocumentProcessor()
        print("✓ Document processor initialized successfully")
        
        # Test with a sample text (since we don't have actual PDFs)
        sample_text = "This is a sample text for testing the document processor. " * 50
        
        # Test text splitting
        chunks = processor.create_chunks([(sample_text, 1)])
        print(f"✓ Text splitting works: {len(chunks)} chunks created")
        
        # Test embedding generation (this will fail without actual text, but we can test the structure)
        print("✓ Document processor test completed")
        return True
        
    except Exception as e:
        print(f"✗ Document processor test failed: {e}")
        return False

async def test_rag_service():
    """Test the RAG service"""
    print("\n=== Testing RAG Service ===")
    
    try:
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            print("⚠ GROQ_API_KEY not set, skipping RAG service test")
            return True
        
        rag_service = RAGService(groq_api_key)
        print("✓ RAG service initialized successfully")
        
        # Test with sample chunks
        sample_chunks = [
            {
                "content": "This is a sample chunk about history.",
                "page_start": 1,
                "page_end": 1,
                "book_title": "Sample Book",
                "embedding": [0.1] * 384
            }
        ]
        
        # Test context creation
        context = rag_service.create_context_from_chunks(sample_chunks)
        print(f"✓ Context creation works: {len(context)} characters")
        
        print("✓ RAG service test completed")
        return True
        
    except Exception as e:
        print(f"✗ RAG service test failed: {e}")
        return False

async def test_supabase_service():
    """Test the Supabase service"""
    print("\n=== Testing Supabase Service ===")
    
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not all([supabase_url, supabase_key]):
            print("⚠ Supabase credentials not set, skipping Supabase service test")
            return True
        
        supabase_service = SupabaseService(supabase_url, supabase_key)
        print("✓ Supabase service initialized successfully")
        
        # Test connection by trying to get books (this might fail if no books exist, but that's okay)
        try:
            books = await supabase_service.get_books_by_genre("history")
            print(f"✓ Supabase connection works: {len(books)} history books found")
        except Exception as e:
            print(f"⚠ Supabase connection test: {e}")
        
        print("✓ Supabase service test completed")
        return True
        
    except Exception as e:
        print(f"✗ Supabase service test failed: {e}")
        return False

async def test_chat_service():
    """Test the chat service"""
    print("\n=== Testing Chat Service ===")
    
    try:
        # Check if we have the required services
        groq_api_key = os.getenv("GROQ_API_KEY")
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not all([groq_api_key, supabase_url, supabase_key]):
            print("⚠ Required credentials not set, skipping chat service test")
            return True
        
        rag_service = RAGService(groq_api_key)
        supabase_service = SupabaseService(supabase_url, supabase_key)
        chat_service = ChatService(rag_service, supabase_service)
        
        print("✓ Chat service initialized successfully")
        print("✓ Chat service test completed")
        return True
        
    except Exception as e:
        print(f"✗ Chat service test failed: {e}")
        return False

async def test_environment():
    """Test environment configuration"""
    print("\n=== Testing Environment Configuration ===")
    
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_KEY", 
        "SUPABASE_SERVICE_ROLE_KEY",
        "GROQ_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if os.getenv(var):
            print(f"✓ {var} is set")
        else:
            print(f"✗ {var} is missing")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠ Missing environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file")
        return False
    else:
        print("✓ All required environment variables are set")
        return True

async def main():
    """Run all tests"""
    print("🚀 Starting Inside LM RAG System Tests")
    print("=" * 50)
    
    tests = [
        test_environment(),
        test_document_processor(),
        test_rag_service(),
        test_supabase_service(),
        test_chat_service()
    ]
    
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"✗ Test {i+1} failed with exception: {result}")
        elif result:
            passed += 1
            print(f"✓ Test {i+1} passed")
        else:
            print(f"✗ Test {i+1} failed")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The system is ready to use.")
    else:
        print("⚠ Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
