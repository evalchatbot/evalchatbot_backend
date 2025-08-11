#!/usr/bin/env python3
"""
Data Ingestion Script for Inside LM
Processes PDF documents and uploads them to the system
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import List, Dict
import asyncio
import logging

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.document_processor import DocumentProcessor
from app.services.supabase_service import SupabaseService
from app.models.database import Genre
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration - Modify these variables to specify file paths directly in code
CONFIG = {
    # Single file ingestion
    "SINGLE_FILE_PATH": "/path/to/your/document.pdf",  # Change this to your PDF path
    "SINGLE_FILE_TITLE": "Your Document Title",        # Optional: specify title
    "SINGLE_FILE_AUTHOR": "Author Name",               # Optional: specify author
    "SINGLE_FILE_GENRE": "history",                    # Optional: specify genre
    
    # Directory ingestion
    "DIRECTORY_PATH": "/path/to/your/pdf/directory",   # Change this to your directory path
    "DIRECTORY_GENRE": "history",                      # Genre for all files in directory
    
    # Config file ingestion
    "CONFIG_FILE_PATH": "/path/to/your/config.json",   # Change this to your config file path
    
    # Default behavior when no command line args are provided
    "DEFAULT_ACTION": "single_file",  # Options: "single_file", "directory", "config", "none"
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataIngestionPipeline:
    def __init__(self):
        self.document_processor = DocumentProcessor()
        
        # Initialize Supabase service
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not all([supabase_url, supabase_key]):
            raise ValueError("Missing required environment variables: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY")
        
        self.supabase_service = SupabaseService(supabase_url, supabase_key)
    
    async def ingest_single_document(
        self, 
        file_path: str, 
        title: str = None, 
        author: str = None, 
        genre: str = "other"
    ) -> Dict:
        """
        Ingest a single PDF document
        """
        try:
            logger.info(f"Processing document: {file_path}")
            
            # Validate file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Validate file is PDF
            if not file_path.lower().endswith('.pdf'):
                raise ValueError(f"File is not a PDF: {file_path}")
            
            # Process document
            chunks = self.document_processor.process_document(file_path)
            
            if not chunks:
                raise ValueError("No chunks generated from document")
            
            # Create book record
            book_data = {
                "title": title or Path(file_path).stem,
                "author": author or "Unknown Author",
                "genre": genre,
                "file_path": file_path,
                "total_pages": max(chunk["page_end"] for chunk in chunks) if chunks else 0
            }
            
            logger.info(f"Creating book record: {book_data['title']} by {book_data['author']}")
            book = await self.supabase_service.create_book(book_data)
            
            if not book:
                raise ValueError("Failed to create book record")
            
            # Add book_id to chunks
            for chunk in chunks:
                chunk["book_id"] = book["id"]
            
            # Store chunks in database
            logger.info(f"Storing {len(chunks)} chunks in database")
            stored_chunks = await self.supabase_service.create_chunks(chunks)
            
            if not stored_chunks:
                raise ValueError("Failed to store document chunks")
            
            logger.info(f"Successfully ingested document: {book_data['title']}")
            
            return {
                "status": "success",
                "book": book,
                "chunks_created": len(stored_chunks),
                "total_pages": book_data["total_pages"]
            }
            
        except Exception as e:
            logger.error(f"Error ingesting document {file_path}: {e}")
            return {
                "status": "error",
                "file_path": file_path,
                "error": str(e)
            }
    
    async def ingest_batch_documents(
        self, 
        documents: List[Dict]
    ) -> List[Dict]:
        """
        Ingest multiple documents
        """
        results = []
        
        for doc in documents:
            result = await self.ingest_single_document(
                file_path=doc["file_path"],
                title=doc.get("title"),
                author=doc.get("author"),
                genre=doc.get("genre", "other")
            )
            results.append(result)
            
            # Small delay to avoid overwhelming the system
            await asyncio.sleep(1)
        
        return results
    
    async def ingest_from_directory(
        self, 
        directory_path: str, 
        genre: str = "other"
    ) -> List[Dict]:
        """
        Ingest all PDF documents from a directory
        """
        directory = Path(directory_path)
        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"Directory not found: {directory_path}")
        
        pdf_files = list(directory.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files in {directory_path}")
        
        documents = []
        for pdf_file in pdf_files:
            documents.append({
                "file_path": str(pdf_file),
                "title": pdf_file.stem,
                "author": "Unknown Author",
                "genre": genre
            })
        
        return await self.ingest_batch_documents(documents)
    
    async def ingest_from_config_file(self, config_file: str) -> List[Dict]:
        """
        Ingest documents based on a configuration file
        """
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        documents = config.get("documents", [])
        logger.info(f"Loaded {len(documents)} documents from config file")
        
        return await self.ingest_batch_documents(documents)

def create_sample_config():
    """Create a sample configuration file"""
    sample_config = {
        "documents": [
            {
                "file_path": "/path/to/document1.pdf",
                "title": "Sample Document 1",
                "author": "John Doe",
                "genre": "history"
            },
            {
                "file_path": "/path/to/document2.pdf",
                "title": "Sample Document 2",
                "author": "Jane Smith",
                "genre": "science"
            }
        ]
    }
    
    config_path = "sample_ingestion_config.json"
    with open(config_path, 'w') as f:
        json.dump(sample_config, f, indent=2)
    
    logger.info(f"Created sample config file: {config_path}")
    return config_path

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Data Ingestion Pipeline for Inside LM")
    parser.add_argument("--file", help="Single PDF file to ingest")
    parser.add_argument("--title", help="Title for the document")
    parser.add_argument("--author", help="Author for the document")
    parser.add_argument("--genre", help="Genre for the document", default="other")
    parser.add_argument("--directory", help="Directory containing PDF files to ingest")
    parser.add_argument("--config", help="Configuration file for batch ingestion")
    parser.add_argument("--create-sample-config", action="store_true", help="Create a sample configuration file")
    
    args = parser.parse_args()
    
    try:
        pipeline = DataIngestionPipeline()
        
        if args.create_sample_config:
            config_path = create_sample_config()
            print(f"Sample config created: {config_path}")
            return
        
        # Use command line arguments if provided, otherwise use CONFIG values
        if args.file:
            # Ingest single file from command line
            result = await pipeline.ingest_single_document(
                file_path=args.file,
                title=args.title,
                author=args.author,
                genre=args.genre
            )
            print(json.dumps(result, indent=2))
            
        elif args.directory:
            # Ingest from directory from command line
            results = await pipeline.ingest_from_directory(args.directory, args.genre)
            print(json.dumps(results, indent=2))
            
        elif args.config:
            # Ingest from config file from command line
            results = await pipeline.ingest_from_config_file(args.config)
            print(json.dumps(results, indent=2))
            
        else:
            # No command line arguments provided, use CONFIG values
            if CONFIG["DEFAULT_ACTION"] == "single_file":
                if CONFIG["SINGLE_FILE_PATH"] == "/path/to/your/document.pdf":
                    print("ERROR: Please modify the CONFIG section at the top of this script to specify your file path.")
                    print("Current CONFIG['SINGLE_FILE_PATH'] is set to the default placeholder value.")
                    return
                
                print(f"Using configured file path: {CONFIG['SINGLE_FILE_PATH']}")
                result = await pipeline.ingest_single_document(
                    file_path=CONFIG["SINGLE_FILE_PATH"],
                    title=CONFIG["SINGLE_FILE_TITLE"] if CONFIG["SINGLE_FILE_TITLE"] != "Your Document Title" else None,
                    author=CONFIG["SINGLE_FILE_AUTHOR"] if CONFIG["SINGLE_FILE_AUTHOR"] != "Author Name" else None,
                    genre=CONFIG["SINGLE_FILE_GENRE"]
                )
                print(json.dumps(result, indent=2))
                
            elif CONFIG["DEFAULT_ACTION"] == "directory":
                if CONFIG["DIRECTORY_PATH"] == "/path/to/your/pdf/directory":
                    print("ERROR: Please modify the CONFIG section at the top of this script to specify your directory path.")
                    print("Current CONFIG['DIRECTORY_PATH'] is set to the default placeholder value.")
                    return
                
                print(f"Using configured directory path: {CONFIG['DIRECTORY_PATH']}")
                results = await pipeline.ingest_from_directory(CONFIG["DIRECTORY_PATH"], CONFIG["DIRECTORY_GENRE"])
                print(json.dumps(results, indent=2))
                
            elif CONFIG["DEFAULT_ACTION"] == "config":
                if CONFIG["CONFIG_FILE_PATH"] == "/path/to/your/config.json":
                    print("ERROR: Please modify the CONFIG section at the top of this script to specify your config file path.")
                    print("Current CONFIG['CONFIG_FILE_PATH'] is set to the default placeholder value.")
                    return
                
                print(f"Using configured config file path: {CONFIG['CONFIG_FILE_PATH']}")
                results = await pipeline.ingest_from_config_file(CONFIG["CONFIG_FILE_PATH"])
                print(json.dumps(results, indent=2))
                
            elif CONFIG["DEFAULT_ACTION"] == "none":
                print("No default action configured. Please provide command line arguments or modify the CONFIG section.")
                parser.print_help()
            else:
                print(f"Invalid DEFAULT_ACTION in CONFIG: {CONFIG['DEFAULT_ACTION']}")
                parser.print_help()
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
