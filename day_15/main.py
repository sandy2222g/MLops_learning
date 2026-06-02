import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag_engine import RAGEngine, DATA_DIR

# Initialize FastAPI App
app = FastAPI(title="Artwork Damage Restoration RAG Assistant", version="1.0.0")

# CORS middleware for local testing flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize global RAG Engine
rag_engine = RAGEngine()

# Request Models
class QueryRequest(BaseModel):
    query: str

class SettingsRequest(BaseModel):
    api_key: str

@app.get("/api/status")
async def get_status():
    """Returns the API configuration status and system statistics."""
    try:
        docs = rag_engine.get_indexed_documents()
        total_chunks = len(rag_engine.index)
        return {
            "api_key_configured": rag_engine.is_api_configured(),
            "indexed_documents_count": len(docs),
            "total_chunks_count": total_chunks,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings")
async def update_settings(req: SettingsRequest):
    """Updates the Gemini API Key dynamically at runtime."""
    if not req.api_key or len(req.api_key.strip()) == 0:
        raise HTTPException(status_code=400, detail="API Key cannot be empty.")
    
    success = rag_engine.set_api_key(req.api_key)
    if success:
        # Optionally write it to the .env file so it persists
        try:
            with open(".env", "w") as f:
                f.write(f"GEMINI_API_KEY={req.api_key}\n")
        except Exception as e:
            print(f"Could not persist API key to .env: {e}")
            
        return {"status": "success", "message": "API key successfully updated and validated."}
    else:
        raise HTTPException(status_code=400, detail="Failed to validate API key. Please check that it is a valid Gemini key.")

@app.get("/api/documents")
async def get_documents():
    """Lists all currently uploaded and indexed documents."""
    try:
        return rag_engine.get_indexed_documents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """Handles uploading a new file, saving it locally, and indexing it in the vector database."""
    # Ensure allowed extensions
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".txt", ".pdf", ".docx"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format '{ext}'. Only .txt, .pdf, and .docx are supported."
        )

    # Clean the filename to prevent path traversal
    filename = os.path.basename(filename)
    dest_path = os.path.join(DATA_DIR, filename)

    try:
        # Save the uploaded file
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Add to index
        result = rag_engine.add_document(dest_path)
        return result
    except Exception as e:
        # Clean up file on failure if it was written
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(status_code=500, detail=f"Failed to process and index file: {str(e)}")

@app.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    """Deletes a document from the disk and removes all its indexed chunks."""
    try:
        success = rag_engine.delete_document(filename)
        if success:
            return {"status": "success", "message": f"Successfully deleted '{filename}' from Knowledge Base."}
        else:
            raise HTTPException(status_code=404, detail=f"Document '{filename}' not found in index.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
async def query_assistant(req: QueryRequest):
    """Queries the RAG system: semantic search over documents + context-aware LLM answer generation."""
    if not req.query or len(req.query.strip()) == 0:
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    try:
        # Step 1: Search relevant chunks (top-k)
        contexts = rag_engine.search_similar_chunks(req.query, top_k=4)
        
        # Step 2: Generate response grounded in context
        response_text, sources = rag_engine.generate_response(req.query, contexts)
        
        return {
            "query": req.query,
            "answer": response_text,
            "sources": sources
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

# Mount the static files directory
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)

# Serves index.html at root
@app.get("/")
async def read_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(
        status_code=404,
        content={"message": "Frontend index.html not found. Please wait for files to generate."}
    )

app.mount("/", StaticFiles(directory=static_dir), name="static")

if __name__ == "__main__":
    import uvicorn
    # Automatically read port from environment or default to 8000
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
