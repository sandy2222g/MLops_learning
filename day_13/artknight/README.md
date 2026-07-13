# Art Restoration Analysis Platform

A full-stack ML web application for artwork analysis with three tools:

| Mode | Description |
|---|---|
| 🎨 **Restoration Prediction** | Predicts restoration difficulty (Easy / Moderate / Difficult / Impossible) using a trained RandomForest model on 21 computer-vision features |
| 🔍 **Damage Detection** | Detects surface cracks in artwork using a fine-tuned YOLOv8 segmentation model |
| 🤖 **RAG Bot** | A conservation knowledge assistant backed by ChromaDB + Gemini / local Ollama LLMs |

---

## Stack

- **Frontend** — React + Vite + Tailwind CSS
- **Backend** — Python Flask
- **CV** — OpenCV, scikit-image
- **ML** — scikit-learn RandomForest, YOLOv8 (Ultralytics)
- **RAG** — ChromaDB, SentenceTransformers, Google Gemini / Ollama

---

## Quick Start (Windows)

```bat
run.bat
```

This will:
1. Create a Python venv in `server/`, install all dependencies
2. Start the Flask backend at `http://localhost:5000`
3. Install Node dependencies and start Vite at `http://localhost:5173`

---

## Project Structure

```
website/
├── client/          # React frontend
├── server/          # Flask backend (all 3 modes)
├── rag/             # RAG engine + ChromaDB + documents
├── yolomodel artwork/  # YOLOv8 trained weights + training notebook
├── model/           # RandomForest training notebook + dataset
├── learning/        # Project documentation
├── run.bat          # One-click launcher
└── docker-compose.yml
```

---

## Environment Setup

### RAG Bot (Gemini API)

```bash
cp rag/.env.example rag/.env
# Edit rag/.env and add your GEMINI_API_KEY
```

Get a free API key at [Google AI Studio](https://aistudio.google.com/apikey).

Alternatively, install [Ollama](https://ollama.com) with a local model — the RAG bot will detect and use it automatically.

### Populate the RAG Knowledge Base

```bash
cd rag
pip install -r requirements.txt
python ingest.py
```

This indexes all documents in `rag/data/` into ChromaDB. You can also upload documents live via the RAG Bot UI.

---

## Large Files (Git LFS)

The following files are **excluded from this repo** due to size. Download or regenerate them:

| File | Size | How to get |
|---|---|---|
| `yolomodel artwork/runs/.../best.pt` | ~52 MB | Re-run `train_yolo.ipynb` or download from releases |
| `model/art_restoration_dataset_new.csv` | ~1.4 MB | Run the training notebook |

The trained RandomForest model (`server/artifacts/art_restoration_model.pkl`) **is included** as it is small enough.

---

## Docker

```bash
docker compose up --build
```

See [DEPLOY.md](DEPLOY.md) for AWS EC2 deployment instructions.
