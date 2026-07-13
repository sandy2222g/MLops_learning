"""
ingest.py

Extracts text from Canadian Conservation Institute (CCI) Notes PDFs,
chunks the text, generates embeddings locally using sentence-transformers,
and stores them in a persistent local Chroma vector database.
"""

import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
import re
from typing import List, Dict, Any
import pypdf
import chromadb
from sentence_transformers import SentenceTransformer

PDF_DIR = "./sandbox/cci_notes"
CHROMA_DIR = "./sandbox/chroma_db"
COLLECTION_NAME = "cci_notes"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


def extract_text(pdf_path: str) -> Dict[str, Any]:
    """
    Extracts plain text from a PDF file and captures the first non-empty line as a potential title.

    Args:
        pdf_path (str): The file path to the PDF document.

    Returns:
        dict: A dictionary containing either:
            - {"text": str, "title": str, "filename": str}
            - {"error": str}
    """
    try:
        if not os.path.exists(pdf_path):
            return {"error": f"File not found: {pdf_path}"}

        filename = os.path.basename(pdf_path)
        text_parts = []
        
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        full_text = "\n".join(text_parts).strip()
        if not full_text:
            return {"error": f"No text could be extracted from {filename}"}

        # Try to find a title from the first few non-empty lines
        lines = [line.strip() for line in full_text.split("\n") if line.strip()]
        title = lines[0] if lines else filename
        # Capping title length to keep it clean
        if len(title) > 150:
            title = title[:147] + "..."

        return {
            "text": full_text,
            "title": title,
            "filename": filename
        }
    except Exception as e:
        return {"error": f"Failed to extract text from {pdf_path}: {str(e)}"}


def chunk_text(text: str, filename: str, title: str) -> Dict[str, Any]:
    """
    Splits document text into paragraph-respecting chunks of roughly 300 to 500 tokens (words).

    Args:
        text (str): The full document text.
        filename (str): The source PDF filename for metadata.
        title (str): The title of the note for metadata.

    Returns:
        dict: A dictionary containing either:
            - {"chunks": [{"text": str, "metadata": dict}, ...]}
            - {"error": str}
    """
    try:
        # Split text into paragraphs based on double newlines or similar breaks
        paragraphs = re.split(r"\n\s*\n", text)
        # If double newlines are not present, split by single newlines
        if len(paragraphs) <= 1:
            paragraphs = text.split("\n")

        chunks = []
        current_chunk_words = []
        current_word_count = 0
        chunk_index = 0

        # Define targets
        MIN_WORDS = 250
        MAX_WORDS = 400

        for para in paragraphs:
            para_clean = para.strip()
            if not para_clean:
                continue

            para_words = para_clean.split()
            para_word_count = len(para_words)

            # If a paragraph itself is huge, split it into sentences
            if para_word_count > MAX_WORDS:
                sentences = re.split(r"(?<=[.!?])\s+", para_clean)
                for sentence in sentences:
                    sentence_clean = sentence.strip()
                    if not sentence_clean:
                        continue
                    sent_words = sentence_clean.split()
                    sent_word_count = len(sent_words)

                    if current_word_count + sent_word_count > MAX_WORDS:
                        # Flush current chunk
                        if current_chunk_words:
                            chunks.append({
                                "text": " ".join(current_chunk_words),
                                "metadata": {
                                    "source": filename,
                                    "title": title,
                                    "chunk_index": chunk_index
                                }
                            })
                            chunk_index += 1
                        current_chunk_words = sent_words
                        current_word_count = sent_word_count
                    else:
                        current_chunk_words.extend(sent_words)
                        current_word_count += sent_word_count
            else:
                if current_word_count + para_word_count > MAX_WORDS:
                    # Flush current chunk
                    if current_chunk_words:
                        chunks.append({
                            "text": " ".join(current_chunk_words),
                            "metadata": {
                                "source": filename,
                                "title": title,
                                "chunk_index": chunk_index
                            }
                        })
                        chunk_index += 1
                    current_chunk_words = para_words
                    current_word_count = para_word_count
                else:
                    current_chunk_words.extend(para_words)
                    current_word_count += para_word_count

            # If we've reached the minimum size, we can flush if the next paragraphs would overflow
            if current_word_count >= MIN_WORDS and current_word_count <= MAX_WORDS:
                # Keep accumulating until we are closer to MAX_WORDS or flush
                pass

        # Flush any remaining words
        if current_chunk_words:
            chunks.append({
                "text": " ".join(current_chunk_words),
                "metadata": {
                    "source": filename,
                    "title": title,
                    "chunk_index": chunk_index
                }
            })

        return {"chunks": chunks}
    except Exception as e:
        return {"error": f"Failed to chunk text for {filename}: {str(e)}"}


def ingest_pdfs(pdf_dir: str = PDF_DIR, chroma_dir: str = CHROMA_DIR) -> Dict[str, Any]:
    """
    Finds all PDFs in the folder, extracts text, chunks, embeds, and loads into Chroma DB.
    Skips files containing '-fra' in their filename.

    Args:
        pdf_dir (str): Directory containing the PDF notes.
        chroma_dir (str): Directory for the persistent Chroma DB.

    Returns:
        dict: A dictionary containing either:
            - {"status": str, "documents_indexed": int, "chunks_added": int}
            - {"error": str}
    """
    try:
        if not os.path.exists(pdf_dir):
            return {"error": f"PDF directory not found: {pdf_dir}"}

        pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]
        # Filter out French duplicates
        pdf_files = [f for f in pdf_files if "-fra" not in f.lower()]

        if not pdf_files:
            return {"error": f"No English PDFs found in directory {pdf_dir}"}

        all_chunks = []
        doc_count = 0

        print(f"Extracting and chunking {len(pdf_files)} PDFs...")
        for filename in pdf_files:
            pdf_path = os.path.join(pdf_dir, filename)
            
            # Extract
            extract_result = extract_text(pdf_path)
            if "error" in extract_result:
                print(f"Skipping {filename}: {extract_result['error']}")
                continue

            # Chunk
            chunk_result = chunk_text(
                extract_result["text"], 
                extract_result["filename"], 
                extract_result["title"]
            )
            if "error" in chunk_result:
                print(f"Skipping {filename}: {chunk_result['error']}")
                continue

            chunks = chunk_result["chunks"]
            all_chunks.extend(chunks)
            doc_count += 1
            print(f"Processed {filename}: created {len(chunks)} chunks")

        if not all_chunks:
            return {"error": "No chunks generated from any PDFs"}

        # Initialize SentenceTransformer
        print(f"Loading local embedding model: {EMBEDDING_MODEL_NAME}...")
        embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

        # Generate embeddings
        print(f"Generating embeddings for {len(all_chunks)} chunks...")
        texts_to_embed = [c["text"] for c in all_chunks]
        embeddings = embedding_model.encode(texts_to_embed, show_progress_bar=True)
        # Convert numpy embeddings to list of lists
        embeddings_list = embeddings.tolist()

        # Initialize Chroma Client
        print(f"Connecting to persistent Chroma DB at {chroma_dir}...")
        chroma_client = chromadb.PersistentClient(path=chroma_dir)
        
        # Reset/delete the collection if it exists to avoid duplication
        try:
            chroma_client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
            
        collection = chroma_client.create_collection(name=COLLECTION_NAME)

        # Add chunks in batches to Chroma DB
        ids = [f"{c['metadata']['source']}_chunk_{c['metadata']['chunk_index']}" for c in all_chunks]
        metadatas = [c["metadata"] for c in all_chunks]
        documents = [c["text"] for c in all_chunks]

        print("Writing embeddings and documents to Chroma DB...")
        collection.add(
            ids=ids,
            embeddings=embeddings_list,
            metadatas=metadatas,
            documents=documents
        )

        return {
            "status": "success",
            "documents_indexed": doc_count,
            "chunks_added": len(all_chunks)
        }
    except Exception as e:
        return {"error": f"Ingestion process failed: {str(e)}"}


if __name__ == "__main__":
    print("Starting ingestion script...")
    result = ingest_pdfs()
    if "error" in result:
        print(f"\nINGESTION FAILED: {result['error']}")
    else:
        print(f"\nINGESTION SUCCESSFUL!")
        print(f"Documents indexed: {result['documents_indexed']}")
        print(f"Chunks added to vector index: {result['chunks_added']}")
