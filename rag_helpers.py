import os
import re
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from db_helpers import get_db_connection
from models_helpers import generate_llm_response

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def extract_text_from_pdf(filepath: str) -> str:
    """Extracts text content from a PDF file using pypdf."""
    text = ""
    try:
        reader = PdfReader(filepath)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
    # Normalize whitespaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def chunk_text(text: str, chunk_size: int = 600, overlap: int = 150) -> list:
    """Splits text into chunks of specified size and overlap."""
    chunks = []
    if not text:
        return chunks
    
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
        if len(text) - start < overlap:
            # If remaining text is less than overlap, grab the rest and stop
            chunks.append(text[start:])
            break
    return [c.strip() for c in chunks if len(c.strip()) > 10]

def add_document(user_id: int, filename: str, file_bytes: bytes, category: str = "General") -> tuple:
    """Saves PDF, parses it, chunks it, and saves metadata/chunks to DB."""
    # Ensure safe filename
    safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    filepath = os.path.join(UPLOAD_DIR, f"{user_id}_{int(os.path.getmtime(UPLOAD_DIR) if os.path.exists(UPLOAD_DIR) else 0)}_{safe_filename}")
    
    try:
        # Save file locally
        with open(filepath, "wb") as f:
            f.write(file_bytes)
        
        file_size = len(file_bytes)
        
        # Parse text and chunk it
        pdf_text = extract_text_from_pdf(filepath)
        if not pdf_text:
            os.remove(filepath)
            return False, "Failed to extract text from PDF (it might be scanned or empty)."
            
        chunks = chunk_text(pdf_text)
        if not chunks:
            os.remove(filepath)
            return False, "No meaningful text chunks found in PDF."
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Save document metadata
        cursor.execute(
            "INSERT INTO documents (user_id, filename, filepath, category, size_bytes) VALUES (?, ?, ?, ?, ?)",
            (user_id, filename, filepath, category, file_size)
        )
        doc_id = cursor.lastrowid
        
        # Save chunks
        chunk_data = [(doc_id, chunk, idx) for idx, chunk in enumerate(chunks)]
        cursor.executemany(
            "INSERT INTO document_chunks (document_id, chunk_text, chunk_index) VALUES (?, ?, ?)",
            chunk_data
        )
        
        conn.commit()
        conn.close()
        return True, f"Successfully uploaded and indexed {len(chunks)} text chunks."
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return False, f"Failed to upload document: {str(e)}"

def delete_document(doc_id: int, user_id: int) -> tuple:
    """Deletes a document from the filesystem and database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT filepath FROM documents WHERE id = ? AND user_id = ?", (doc_id, user_id))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False, "Document not found."
            
        filepath = row['filepath']
        
        # Delete file from disk
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as fe:
                print(f"Error removing file: {fe}")
                
        # Delete from database (cascades automatically to document_chunks)
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        return True, "Document deleted successfully."
    except Exception as e:
        return False, f"Database error: {str(e)}"
    finally:
        conn.close()

def get_user_documents(user_id: int) -> list:
    """Fetches list of all uploaded documents for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def query_rag(user_id: int, query_text: str, model_name: str, api_key: str = None) -> dict:
    """
    RAG engine: Retrieves matching PDF text chunks using TF-IDF similarity,
    and queries the LLM with context.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Fetch all chunks for this user's uploaded documents
    cursor.execute("""
        SELECT dc.chunk_text, dc.chunk_index, d.filename, d.id as doc_id
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE d.user_id = ?
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return {
            "answer": "You haven't uploaded any documents yet. Please upload a PDF technical document first in the Document Management dashboard.",
            "sources": [],
            "confidence": 0.0,
            "latency_ms": 0
        }
    
    chunks = [row['chunk_text'] for row in rows]
    chunk_meta = [dict(row) for row in rows]
    
    # 2. Vectorize chunks and query
    vectorizer = TfidfVectorizer(stop_words='english')
    try:
        tfidf_matrix = vectorizer.fit_transform(chunks)
        query_vector = vectorizer.transform([query_text])
        
        # 3. Calculate cosine similarity
        similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
        
        # 4. Get top indices (up to 4 chunks)
        top_indices = np.argsort(similarities)[::-1]
        top_k = min(4, len(chunks))
        matched_indices = top_indices[:top_k]
    except Exception as ve:
        print(f"TFIDF Error: {ve}")
        matched_indices = range(min(4, len(chunks)))
        similarities = [0.5] * len(chunks)
        
    sources = []
    context_blocks = []
    max_sim = 0.0
    
    for idx in matched_indices:
        sim_score = float(similarities[idx])
        if sim_score > max_sim:
            max_sim = sim_score
            
        chunk_info = chunk_meta[idx]
        sources.append({
            "filename": chunk_info['filename'],
            "excerpt": chunk_info['chunk_text'][:200] + "...",
            "similarity": sim_score
        })
        context_blocks.append(f"Source Document: {chunk_info['filename']} (Chunk {chunk_info['chunk_index']}):\n{chunk_info['chunk_text']}")
        
    # Map cosine similarity to confidence score [0.0, 1.0]
    # Simple mapping: standard TF-IDF similarity of >0.15 is generally a good match
    confidence = min(1.0, max_sim / 0.4) if max_sim > 0.0 else 0.2
    
    # 5. Build context-aware prompt
    context = "\n\n---\n\n".join(context_blocks)
    prompt = f"""You are a helpful AI Tutor. You are answering a student's question based strictly on the provided technical documents context.
If the context does not contain enough information to answer the question, state that clearly, but try to answer as best as you can using the context.

STUDENT QUESTION: {query_text}

PROVIDED DOCUMENTS CONTEXT:
{context}

Please provide a detailed, educational answer referencing the sources when appropriate:"""

    system_instruction = "You are an AI Tutor answering questions based on uploaded documents. Keep answers educational and cite sources."
    answer, latency = generate_llm_response(prompt, model_name, api_key, system_instruction)
    
    return {
        "answer": answer,
        "sources": sources,
        "confidence": round(confidence, 2),
        "latency_ms": latency
    }
