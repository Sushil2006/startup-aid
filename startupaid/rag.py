import os
import fitz  # PyMuPDF
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
from qdrant_client.http.exceptions import UnexpectedResponse

# Initialize the sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')
EMBEDDING_SIZE = 384  # Embedding size for the chosen model

def create_collection(collection_name: str = "ai_grader") -> None:
    """
    Create a Qdrant collection if it doesn't exist.
    
    Args:
        collection_name: Name of the collection to create
    """
    try:
        client = QdrantClient("localhost", port=6333)
        
        # Check if collection exists
        try:
            client.get_collection(collection_name)
            print(f"Collection '{collection_name}' already exists.")
        except UnexpectedResponse:
            # Create new collection
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=EMBEDDING_SIZE, distance=Distance.COSINE),
            )
            print(f"Collection '{collection_name}' created successfully.")
    except Exception as e:
        print(f"Error creating collection: {str(e)}")

def split_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: The text to split
        chunk_size: Maximum size of each chunk
        overlap: Overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = min(start + chunk_size, text_len)
        # If we're not at the beginning, back up to include overlap
        if start > 0:
            start = start - overlap
        
        # Get the chunk and add to list
        chunk = text[start:end]
        chunks.append(chunk)
        
        # Move to next chunk position
        start = end
    
    return chunks

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract all text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        String containing all text extracted from the PDF
    """
    try:
        # Open the PDF
        pdf_document = fitz.open(pdf_path)
        text = ""
        
        # Extract text from each page
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            text += page.get_text()
            text += "\n\n"  # Add spacing between pages
            
        pdf_document.close()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
        return ""

def add_pdf_to_vector_db(pdf_path: str, collection_name: str = "ai_grader", metadata: Optional[Dict[str, Any]] = None) -> bool:
    """
    Extract text from a PDF, split it into chunks, and add to Qdrant.
    
    Args:
        pdf_path: Path to the PDF file
        collection_name: Name of the Qdrant collection to use
        metadata: Optional metadata to store with the PDF chunks
        
    Returns:
        Boolean indicating success or failure
    """
    try:
        # Extract text from PDF
        text = extract_text_from_pdf(pdf_path)
        
        if not text:
            print(f"No text extracted from {pdf_path}")
            return False
        
        # Split text into chunks
        chunks = split_text(text)
        
        if not chunks:
            print(f"No chunks created from {pdf_path}")
            return False
        
        # Set default metadata if not provided
        if metadata is None:
            file_name = os.path.basename(pdf_path)
            metadata = {"source": file_name}
        
        # Initialize Qdrant client
        client = QdrantClient("localhost", port=6333)
        
        # Generate embeddings and add to Qdrant
        points = []
        for i, chunk in enumerate(chunks):
            # Generate embedding
            embedding = model.encode(chunk)
            
            # Create point with embedding, payload, and unique ID
            point_id = f"{os.path.basename(pdf_path)}_{i}"
            
            # Create point
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=embedding.tolist(),
                    payload={
                        "text": chunk,
                        "source": metadata.get("source", "unknown"),
                        "chunk_id": i,
                        "metadata": metadata
                    }
                )
            )
        
        # Upsert points in batches
        client.upsert(
            collection_name=collection_name,
            points=points
        )
        
        print(f"Successfully added {len(chunks)} chunks from {pdf_path} to Qdrant collection '{collection_name}'")
        return True
    
    except Exception as e:
        print(f"Error adding PDF to vector DB: {str(e)}")
        return False

def retrieve_relevant_text(query_text: str, top_k: int = 5, collection_name: str = "ai_grader") -> str:
    """
    Retrieve the most relevant text chunks for a query.
    
    Args:
        query_text: The query text to find relevant chunks for
        top_k: Number of top results to retrieve
        collection_name: Name of the Qdrant collection to query
        
    Returns:
        Concatenated string of relevant text chunks
    """
    try:
        # Initialize Qdrant client
        client = QdrantClient("localhost", port=6333)
        
        # Generate embedding for query
        query_embedding = model.encode(query_text)
        
        # Search for similar chunks
        search_results = client.search(
            collection_name=collection_name,
            query_vector=query_embedding.tolist(),
            limit=top_k
        )
        
        # Extract and concatenate text from results
        relevant_texts = []
        for result in search_results:
            chunk_text = result.payload.get("text", "")
            if chunk_text:
                relevant_texts.append(chunk_text)
        
        # Join all texts with newlines in between
        concatenated_text = "\n\n".join(relevant_texts)
        
        return concatenated_text
    
    except Exception as e:
        print(f"Error retrieving relevant text: {str(e)}")
        return ""

if __name__ == "__main__":
    # Example usage
    create_collection()
    # Demo PDF path
    # add_pdf_to_vector_db("path_to_pdf.pdf")
    # result = retrieve_relevant_text("Sample query")
    # print(result)
