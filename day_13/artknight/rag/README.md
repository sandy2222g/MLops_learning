# AURA // Artwork Restoration Assistant (RAG)

AURA is a Retrieval-Augmented Generation (RAG) assistant designed to help conservators and restorers by answering questions strictly based on the Canadian Conservation Institute (CCI) Notes. 

It supports:
1. **Local LLMs** via Ollama (e.g., Qwen 2.5 Coder, Phi-3, Mistral, TinyLlama) with dynamic GPU/CPU offloading.
2. **Cloud LLMs** via the Google Gemini API (Gemini 2.5 Flash, Gemini 2.0 Flash, Gemini 1.5 Pro).
3. **Local Text Embeddings** using `sentence-transformers` and a persistent local `Chroma` vector database.

---

## 🚀 Quick Start (Recommended)

Helper scripts are provided to manage setup and run the application automatically.

### On Windows (Command Prompt / PowerShell)
Double-click `run.bat` or run it from the command line:
```cmd
run.bat
```

### On Git Bash / Linux / macOS
Run the bash script:
```bash
chmod +x run.sh
./run.sh
```

---

## 🛠️ Step-by-Step Manual Guide

If you prefer to run the components manually, follow these steps:

### 1. Setup Virtual Environment & Install Dependencies
Ensure you have Python 3.9+ installed. Run:
```bash
# Create a virtual environment
python -m venv .venv

# Activate it (Windows CMD)
.venv\Scripts\activate.bat

# Activate it (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate it (Bash/macOS/Linux)
source .venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

### 2. Prepare the Knowledge Base
To populate the database with CCI notes, you can download them and then ingest them.

#### A. Download PDFs (Optional)
The project comes with some pre-loaded PDFs. If you need to refresh or download all latest PDFs:
```bash
python webscrap.py
```
*This downloads the PDF notes from the official CCI website and saves them under `./sandbox/cci_notes/`.*

#### B. Index the PDFs (Optional)
If you want to re-ingest and re-generate embeddings for the downloaded PDFs:
```bash
python ingest.py
```
*This extracts text, chunks it, generates embeddings using `all-MiniLM-L6-v2` locally, and stores them in the persistent database under `./sandbox/chroma_db/`.*

### 3. Configure API Keys / Local LLMs (Optional)
The assistant can use local or cloud models:
- **For Cloud models (Gemini):** Create a `.env` file in the root directory (or use the UI/CLI setup to create it automatically) and add:
  ```env
  GEMINI_API_KEY=your_gemini_api_key_here
  ```
- **For Local models (Ollama):** Ensure [Ollama](https://ollama.com/) is installed and running (`ollama serve`). The RAG engine will auto-detect Ollama and attempt to use/pull the most suitable model.

---

## 🎮 How to Interact with the Assistant

### Option A: Web Application (UI + Server)
Starts a FastAPI backend and serves a clean web interface at [http://127.0.0.1:8000](http://127.0.0.1:8000):
```bash
python server.py
```
Open your browser and navigate to `http://127.0.0.1:8000` to access the full UI dashboard where you can:
- Ask questions.
- Upload/delete documents in real time.
- Switch models (Gemini cloud vs. Ollama local).
- View GPU VRAM metrics.

### Option B: Interactive CLI Loop
Runs a lightweight chat loop directly in the terminal:
```bash
python main.py
```
*Simply type your questions to search the vector database and generate answers.*

---

## 📁 Key File Descriptions

- [server.py](file:///d:/projects to be explained/rag/server.py): FastAPI server, API endpoints, and static folder mount.
- [main.py](file:///d:/projects to be explained/rag/main.py): CLI interactive query shell.
- [rag_engine.py](file:///d:/projects to be explained/rag/rag_engine.py): Main RAG pipeline orchestrator (model handling, database queries, prompts).
- [ingest.py](file:///d:/projects to be explained/rag/ingest.py): Processes and indexes PDFs.
- [webscrap.py](file:///d:/projects to be explained/rag/webscrap.py): Scrapes and downloads PDF CCI notes.
- [requirements.txt](file:///d:/projects to be explained/rag/requirements.txt): List of Python dependency packages.
