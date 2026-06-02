import os
import json
import re
import numpy as np
import pypdf
import docx2txt
import google.generativeai as genai
from typing import List, Dict, Any, Tuple, Optional

# Constants
DATA_DIR = "data"
INDEX_FILE = os.path.join(DATA_DIR, "vector_index.json")
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

class RAGEngine:
    def __init__(self):
        self.api_key: Optional[str] = None
        self.index: List[Dict[str, Any]] = []
        self._load_index()
        self._load_api_key_from_env()

    def _load_api_key_from_env(self):
        """Loads Gemini API key from environment variables if present."""
        # Load from .env if present
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            self.set_api_key(api_key)

    def set_api_key(self, api_key: str) -> bool:
        """Configures the Google Generative AI client with the provided API key."""
        if not api_key:
            return False
        try:
            genai.configure(api_key=api_key)
            self.api_key = api_key
            # Quick test of configuration
            model = genai.GenerativeModel("models/gemini-1.5-flash")
            # If configure succeeded, we set it
            return True
        except Exception as e:
            print(f"Error configuring Gemini API: {e}")
            return False

    def is_api_configured(self) -> bool:
        """Checks if the Gemini API key is configured."""
        return self.api_key is not None and len(self.api_key.strip()) > 0

    def _load_index(self):
        """Loads the vector index from disk."""
        if os.path.exists(INDEX_FILE):
            try:
                with open(INDEX_FILE, "r", encoding="utf-8") as f:
                    self.index = json.load(f)
                print(f"Loaded vector index with {len(self.index)} chunks.")
            except Exception as e:
                print(f"Error loading vector index: {e}")
                self.index = []
        else:
            self.index = []

    def _save_index(self):
        """Saves the vector index to disk."""
        try:
            with open(INDEX_FILE, "w", encoding="utf-8") as f:
                json.dump(self.index, f, ensure_ascii=False, indent=2)
            print(f"Saved vector index with {len(self.index)} chunks.")
        except Exception as e:
            print(f"Error saving vector index: {e}")

    def extract_text(self, file_path: str) -> str:
        """Extracts plain text from TXT, PDF, or DOCX files."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext == ".pdf":
            text = []
            with open(file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text.append(page_text)
            return "\n".join(text)
        elif ext == ".docx":
            return docx2txt.process(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def chunk_text(self, text: str, filename: str) -> List[Dict[str, Any]]:
        """Splits text into overlapping chunks of roughly equal size."""
        # Clean white spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        chunks = []
        start = 0
        text_len = len(text)
        
        chunk_idx = 0
        while start < text_len:
            end = min(start + CHUNK_SIZE, text_len)
            
            # If not at the end of text, try to find a natural boundary (sentence or space)
            if end < text_len:
                # Find the last period, question mark, exclamation, or space
                boundary = -1
                for char in ['. ', '? ', '! ', ' ']:
                    r_idx = text.rfind(char, start + CHUNK_SIZE - 100, end)
                    if r_idx != -1:
                        boundary = max(boundary, r_idx + len(char))
                
                if boundary != -1:
                    end = boundary

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "id": f"{filename}_chunk_{chunk_idx}",
                    "filename": filename,
                    "chunk_index": chunk_idx,
                    "text": chunk_text,
                    "start_char": start,
                    "end_char": end
                })
                chunk_idx += 1
                
            start = end - CHUNK_OVERLAP
            if start >= text_len or end >= text_len:
                break
                
        return chunks

    def generate_embeddings_batch(self, texts: List[str], is_query: bool = False) -> List[List[float]]:
        """Generates embedding vectors for a list of texts using Gemini API."""
        if not self.is_api_configured():
            # Return mock embeddings for demonstration purposes if API key is missing
            print("WARNING: Gemini API is not configured. Generating mock embeddings.")
            return [self._generate_mock_embedding(text) for text in texts]

        try:
            task_type = "retrieval_query" if is_query else "retrieval_document"
            
            # API has a limit on batch size, but usually 10-20 at once is perfectly fine.
            # We process in batches of 16 just in case.
            all_embeddings = []
            batch_size = 16
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                response = genai.embed_content(
                    model="models/text-embedding-004",
                    content=batch_texts,
                    task_type=task_type
                )
                
                # Check format of response
                if 'embedding' in response:
                    # In some versions of Google GenAI SDK, batch requests return a list of embeddings under 'embedding'
                    embeddings = response['embedding']
                    # Double check if it's a list of lists or just a single list (when batch has only 1 element)
                    if len(batch_texts) == 1 and not isinstance(embeddings[0], list):
                        all_embeddings.append(embeddings)
                    else:
                        all_embeddings.extend(embeddings)
                else:
                    # Fallback or alternative return structure
                    print(f"Unexpected embedding response format: {response.keys()}")
                    all_embeddings.extend([self._generate_mock_embedding(t) for t in batch_texts])
                    
            return all_embeddings
        except Exception as e:
            print(f"Error generating embeddings via Gemini: {e}. Falling back to mock embeddings.")
            return [self._generate_mock_embedding(text) for text in texts]

    def _generate_mock_embedding(self, text: str, dimension: int = 768) -> List[float]:
        """Generates a reproducible pseudo-random unit vector based on the string hash."""
        # Simple deterministic hashing to produce a vector
        val = sum(ord(c) * (i + 1) for i, c in enumerate(text[:100]))
        np.random.seed(val % 2**32)
        vec = np.random.normal(0, 1, dimension)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def add_document(self, file_path: str) -> Dict[str, Any]:
        """Parses a document, chunks it, generates embeddings, and saves to the index."""
        filename = os.path.basename(file_path)
        
        # Remove existing chunks for this file if we are re-indexing
        self.delete_document(filename, save_after=False)
        
        print(f"Processing document: {filename}")
        text = self.extract_text(file_path)
        chunks = self.chunk_text(text, filename)
        
        if not chunks:
            return {"status": "success", "chunks_count": 0, "message": "Document was empty."}
            
        print(f"Split document into {len(chunks)} chunks. Generating embeddings...")
        texts_to_embed = [c["text"] for c in chunks]
        embeddings = self.generate_embeddings_batch(texts_to_embed, is_query=False)
        
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding
            self.index.append(chunk)
            
        self._save_index()
        return {"status": "success", "chunks_count": len(chunks), "message": f"Successfully indexed {filename}."}

    def delete_document(self, filename: str, save_after: bool = True) -> bool:
        """Deletes all chunks associated with a filename from the index."""
        initial_len = len(self.index)
        self.index = [chunk for chunk in self.index if chunk["filename"] != filename]
        deleted_count = initial_len - len(self.index)
        
        # Also delete the local file if it exists in the data directory
        local_path = os.path.join(DATA_DIR, filename)
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception as e:
                print(f"Error removing physical file {filename}: {e}")
                
        if deleted_count > 0 and save_after:
            self._save_index()
            
        return deleted_count > 0

    def get_indexed_documents(self) -> List[Dict[str, Any]]:
        """Returns metadata about the currently indexed documents."""
        docs = {}
        for chunk in self.index:
            fname = chunk["filename"]
            if fname not in docs:
                file_path = os.path.join(DATA_DIR, fname)
                size_bytes = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                docs[fname] = {
                    "filename": fname,
                    "chunks": 0,
                    "size_bytes": size_bytes
                }
            docs[fname]["chunks"] += 1
            
        return list(docs.values())

    def search_similar_chunks(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Searches the index for chunks most semantically similar to the query."""
        if not self.index:
            return []

        # Generate embedding for the query
        query_embeddings = self.generate_embeddings_batch([query], is_query=True)
        if not query_embeddings:
            return []
        query_vec = np.array(query_embeddings[0])

        results = []
        for chunk in self.index:
            chunk_vec = np.array(chunk["embedding"])
            
            # Compute Cosine Similarity
            dot_product = np.dot(query_vec, chunk_vec)
            norm_q = np.linalg.norm(query_vec)
            norm_c = np.linalg.norm(chunk_vec)
            
            similarity = dot_product / (norm_q * norm_c + 1e-9)
            
            # Copy chunk data and add similarity score, exclude raw embedding from search response to save bandwidth
            chunk_copy = {k: v for k, v in chunk.items() if k != "embedding"}
            chunk_copy["similarity"] = float(similarity)
            results.append(chunk_copy)

        # Sort by similarity descending
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def generate_response(self, query: str, contexts: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
        """Generates a response to the query based strictly on the retrieved context chunks."""
        if not contexts:
            return (
                "I couldn't find any information in the uploaded restoration guidelines and files to answer your question. "
                "Please upload relevant conservation documents to my Knowledge Base first, or verify your query.", 
                []
            )

        # Build prompt
        context_str = ""
        for i, ctx in enumerate(contexts):
            context_str += f"Source [{i+1}] ({ctx['filename']}):\n{ctx['text']}\n\n"

        prompt = f"""You are an Artwork Damage Restoration Assistant. You are a world-class conservation and restoration expert.
Your job is to provide professional, clear, and actionable advice to restorers, students, and conservationists.

CRITICAL INSTRUCTION: You MUST answer the user's question based strictly on the provided context sources. 
* Do not make up facts.
* If the context does not contain enough information to answer the question, state clearly that you cannot find sufficient guidance in the current Knowledge Base, but outline what *is* available.
* When referencing facts, cite them as [Source 1], [Source 2], etc., corresponding to the documents below.

---
RELEVANT KNOWLEDGE CONTEXT:
{context_str}
---

USER QUESTION:
{query}

ARTWORK DAMAGE RESTORATION ASSISTANT RESPONSE:"""

        if not self.is_api_configured():
            # Return a professional mock response if Gemini API key is missing
            mock_resp = f"[MOCK MODE - Gemini API Key is Not Set]\n\nBased on your query '{query}', I found the following relevant matches in your documents:\n\n"
            for i, ctx in enumerate(contexts):
                mock_resp += f"* **[Source {i+1}] {ctx['filename']} (Similarity: {ctx['similarity']:.1%}):** \"{ctx['text'][:150]}...\"\n\n"
            mock_resp += "\n*Note: To receive a fully synthesized generative answer, please set your Gemini API key in the Settings panel.*"
            return mock_resp, contexts

        try:
            model = genai.GenerativeModel("models/gemini-1.5-flash")
            response = model.generate_content(prompt)
            return response.text, contexts
        except Exception as e:
            error_msg = f"Error generating answer with Gemini: {e}\n\nHere is what I retrieved:\n\n"
            for i, ctx in enumerate(contexts):
                error_msg += f"- **[Source {i+1}] {ctx['filename']}:** {ctx['text']}\n"
            return error_msg, contexts
