import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
import json
import re
import time
import subprocess
import requests as http_requests
import numpy as np
import pypdf
import docx2txt
import google.generativeai as genai
from typing import List, Dict, Any, Tuple, Optional

# --- Optional Chroma / SentenceTransformers ---
try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_DIR = "data"
CHROMA_DIR = "./sandbox/chroma_db"
COLLECTION_NAME = "cci_notes"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
OLLAMA_BASE_URL = "http://localhost:11434"

# ---------------------------------------------------------------------------
# Model Registry
# Every entry: id, label, type ("gemini" | "ollama"), requires_api_key
# ---------------------------------------------------------------------------
SUPPORTED_MODELS: List[Dict[str, Any]] = [
    # ── Gemini Cloud ──
    {
        "id": "gemini-2.5-flash",
        "label": "Gemini 2.5 Flash (Cloud)",
        "type": "gemini",
        "requires_api_key": True,
        "description": "Google's fastest, most efficient Gemini model.",
    },
    {
        "id": "gemini-2.0-flash",
        "label": "Gemini 2.0 Flash (Cloud)",
        "type": "gemini",
        "requires_api_key": True,
        "description": "Balanced speed and quality from Google.",
    },
    {
        "id": "gemini-1.5-pro",
        "label": "Gemini 1.5 Pro (Cloud)",
        "type": "gemini",
        "requires_api_key": True,
        "description": "Highest quality Google model with large context.",
    },
    # ── Ollama Local (small, fast) ──
    {
        "id": "qwen2.5-coder:7b",
        "label": "Qwen 2.5 Coder 7B (Local)",
        "type": "ollama",
        "requires_api_key": False,
        "description": "Powerful 7B local model by Alibaba. No internet needed.",
        "size_hint": "~4.4 GB",
    },
    {
        "id": "tinyllama:latest",
        "label": "TinyLlama 1.1B (Local, Fast)",
        "type": "ollama",
        "requires_api_key": False,
        "description": "Ultra-small 1.1B model. Very fast, low memory.",
        "size_hint": "~637 MB",
    },
    {
        "id": "phi3:mini",
        "label": "Phi-3 Mini 3.8B (Local)",
        "type": "ollama",
        "requires_api_key": False,
        "description": "Microsoft's compact Phi-3 model. Great quality/size ratio.",
        "size_hint": "~2.2 GB",
    },
    {
        "id": "mistral:7b",
        "label": "Mistral 7B (Local)",
        "type": "ollama",
        "requires_api_key": False,
        "description": "Fast and capable open-source 7B model.",
        "size_hint": "~4.1 GB",
    },
]

# ---------------------------------------------------------------------------
# Helpers — Ollama discovery & pull
# ---------------------------------------------------------------------------

def get_ollama_installed_models() -> List[str]:
    """Returns list of model names currently pulled in Ollama, or [] if Ollama is not running."""
    try:
        resp = http_requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []


def pull_ollama_model(model_id: str) -> Dict[str, Any]:
    """
    Streams an `ollama pull` for the given model and waits for it to finish.
    Returns {"success": True} or {"success": False, "error": str}.
    """
    print(f"[Ollama] Pulling model '{model_id}' — this may take a while...")
    try:
        resp = http_requests.post(
            f"{OLLAMA_BASE_URL}/api/pull",
            json={"name": model_id},
            stream=True,
            timeout=600,
        )
        for line in resp.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    status = chunk.get("status", "")
                    if "total" in chunk and "completed" in chunk:
                        pct = int(100 * chunk["completed"] / chunk["total"])
                        print(f"\r  Downloading {model_id}: {pct}%", end="", flush=True)
                    elif status:
                        print(f"  [{model_id}] {status}")
                    if chunk.get("status") == "success":
                        print(f"\n[Ollama] Model '{model_id}' pulled successfully.")
                        return {"success": True}
                except json.JSONDecodeError:
                    pass
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# GPU detection
# ---------------------------------------------------------------------------

def get_gpu_info() -> Dict[str, Any]:
    """
    Returns GPU info from nvidia-smi.
    Returns {"available": False} if no NVIDIA GPU / driver found.
    """
    try:
        result = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=name,memory.total,memory.free,driver_version,compute_cap",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=8
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = [p.strip() for p in result.stdout.strip().split(",")]
            return {
                "available": True,
                "name": parts[0],
                "vram_total_mb": int(parts[1]),
                "vram_free_mb": int(parts[2]),
                "driver": parts[3],
                "compute_cap": parts[4],
            }
    except Exception:
        pass
    return {"available": False}


def compute_num_gpu_layers(model_id: str, vram_free_mb: int) -> int:
    """
    Estimates how many layers to offload to GPU based on free VRAM.
    Uses a conservative estimate: 200 MB per billion parameters.
    Returns 99 (= all layers) if the model fits, otherwise a partial count,
    and 0 if less than 1 GB free (fall back to CPU).
    """
    # Approximate model sizes in MB for known models
    APPROX_SIZES_MB = {
        "tinyllama": 700,
        "phi3:mini": 2400,
        "phi3": 2400,
        "mistral:7b": 4200,
        "mistral": 4200,
        "qwen2.5-coder:7b": 4700,
        "qwen2.5-coder": 4700,
        "llama3": 4800,
    }
    model_base = model_id.split(":")[0].lower()
    model_size_mb = APPROX_SIZES_MB.get(model_id.lower(),
                    APPROX_SIZES_MB.get(model_base, 4000))

    # Reserve 512 MB for OS + Ollama overhead
    usable_vram_mb = max(0, vram_free_mb - 512)

    if usable_vram_mb < 1024:
        print(f"[GPU] Only {usable_vram_mb} MB usable VRAM — running {model_id} on CPU.")
        return 0  # CPU only

    if usable_vram_mb >= model_size_mb:
        print(f"[GPU] {usable_vram_mb} MB free VRAM ≥ {model_size_mb} MB model — full GPU offload.")
        return 99  # all layers
    else:
        # Partial offload: proportional
        fraction = usable_vram_mb / model_size_mb
        # Typical layer counts: tinyllama=22, 7B=32, 13B=40
        total_layers = 22 if "tiny" in model_base else 32
        num_layers = max(1, int(total_layers * fraction))
        print(f"[GPU] Partial offload: {num_layers}/{total_layers} layers (VRAM {usable_vram_mb}/{model_size_mb} MB)")
        return num_layers


def detect_and_ensure_local_model() -> Optional[str]:
    """
    Checks Ollama for any installed model from our registry.
    Prefers models that fit in GPU VRAM. If none found, downloads the
    smallest suitable model automatically.
    Returns the model id that is ready, or None if Ollama is not available.
    """
    installed = get_ollama_installed_models()
    if not installed and installed is not None:
        installed = []  # empty list means Ollama is up but no models
    elif installed is None:
        return None  # Ollama not reachable

    gpu = get_gpu_info()
    vram_free = gpu.get("vram_free_mb", 0) if gpu["available"] else 0

    if gpu["available"]:
        print(f"[GPU] Detected: {gpu['name']} | "
              f"VRAM: {gpu['vram_total_mb']} MB total, {vram_free} MB free")
    else:
        print("[GPU] No NVIDIA GPU detected — will use CPU for Ollama.")

    # Check registry models in priority order
    # Prefer smaller models if VRAM is tight (< 3 GB free)
    if vram_free < 3000:
        preferred_order = ["tinyllama:latest", "phi3:mini", "qwen2.5-coder:7b", "mistral:7b"]
    else:
        preferred_order = ["qwen2.5-coder:7b", "mistral:7b", "phi3:mini", "tinyllama:latest"]

    for model_id in preferred_order:
        for inst in installed:
            if inst == model_id or inst.startswith(model_id.split(":")[0]):
                print(f"[Ollama] Found local model: {inst}")
                return inst

    # Any installed model will do
    if installed:
        print(f"[Ollama] Using first available model: {installed[0]}")
        return installed[0]

    # Nothing installed → pick best downloadable model based on VRAM
    if vram_free >= 4000:
        to_pull = "qwen2.5-coder:7b"
        size_hint = "~4.4 GB"
    elif vram_free >= 2000:
        to_pull = "phi3:mini"
        size_hint = "~2.2 GB"
    else:
        to_pull = "tinyllama:latest"
        size_hint = "~637 MB"

    print(f"[Ollama] No local models found. Downloading {to_pull} ({size_hint})...")
    result = pull_ollama_model(to_pull)
    if result["success"]:
        return to_pull
    else:
        print(f"[Ollama] Failed to pull {to_pull}: {result.get('error')}")
        return None


# ---------------------------------------------------------------------------
# RAGEngine
# ---------------------------------------------------------------------------

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)


class RAGEngine:
    def __init__(self):
        self.api_key: Optional[str] = None
        self.selected_model: str = "gemini-2.5-flash"  # default
        self._gpu_info: Dict[str, Any] = get_gpu_info()  # cache GPU info

        if self._gpu_info["available"]:
            print(f"[RAGEngine] GPU: {self._gpu_info['name']} | "
                  f"{self._gpu_info['vram_total_mb']} MB VRAM")
        else:
            print("[RAGEngine] No GPU detected. Models will run on CPU.")

        # --- Auto-detect local models first ---
        print("[RAGEngine] Scanning for local Ollama models...")
        local_model = detect_and_ensure_local_model()
        if local_model:
            self.selected_model = local_model
            # Normalize: ensure it appears in our registry
            self._ensure_model_in_registry(local_model)
            print(f"[RAGEngine] Default model set to local: {local_model}")
        else:
            print("[RAGEngine] No Ollama available — defaulting to Gemini (API key required).")

        self._load_api_key_from_env()

        if CHROMA_AVAILABLE:
            print(f"Connecting to persistent Chroma DB at {CHROMA_DIR}...")
            self.chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
            self.collection = self.chroma_client.get_or_create_collection(name=COLLECTION_NAME)
            print(f"Loading local embedding model: {EMBEDDING_MODEL_NAME}...")
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        else:
            self.chroma_client = None
            self.collection = None
            self.embedding_model = None

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------

    def _ensure_model_in_registry(self, model_id: str):
        """Adds a discovered local model to SUPPORTED_MODELS if not already there."""
        for m in SUPPORTED_MODELS:
            if m["id"] == model_id:
                return
        SUPPORTED_MODELS.append({
            "id": model_id,
            "label": f"{model_id} (Local)",
            "type": "ollama",
            "requires_api_key": False,
            "description": f"Locally installed Ollama model: {model_id}",
            "size_hint": "Installed",
        })

    def get_gpu_status(self) -> Dict[str, Any]:
        """Returns the cached GPU information."""
        # Refresh free VRAM on every call
        fresh = get_gpu_info()
        self._gpu_info = fresh
        return fresh

    def get_supported_models(self) -> List[Dict[str, Any]]:
        """Returns the model list annotated with which Ollama models are installed."""
        installed = get_ollama_installed_models()
        result = []
        for m in SUPPORTED_MODELS:
            entry = dict(m)
            if m["type"] == "ollama":
                entry["installed"] = any(
                    inst == m["id"] or inst.startswith(m["id"].split(":")[0])
                    for inst in installed
                )
            else:
                entry["installed"] = True  # cloud models are always "available"
            result.append(entry)

        # Also add any discovered Ollama models not in registry
        registry_ids = {m["id"] for m in SUPPORTED_MODELS}
        for inst in installed:
            if inst not in registry_ids:
                result.append({
                    "id": inst,
                    "label": f"{inst} (Local)",
                    "type": "ollama",
                    "requires_api_key": False,
                    "description": f"Locally installed Ollama model.",
                    "installed": True,
                })
        return result

    def set_model(self, model_id: str) -> bool:
        """Sets the active LLM model. Returns True if valid."""
        all_ids = [m["id"] for m in self.get_supported_models()]
        if model_id not in all_ids:
            print(f"[RAGEngine] Unknown model id: {model_id}")
            return False
        self.selected_model = model_id
        print(f"[RAGEngine] Model switched to: {model_id}")
        return True

    def get_selected_model(self) -> str:
        return self.selected_model

    def is_model_ollama(self, model_id: Optional[str] = None) -> bool:
        mid = model_id or self.selected_model
        for m in SUPPORTED_MODELS:
            if m["id"] == mid:
                return m["type"] == "ollama"
        # Unknown model: guess by name pattern
        return ":" in mid or "/" not in mid

    # ------------------------------------------------------------------
    # API Key management
    # ------------------------------------------------------------------

    def _load_api_key_from_env(self):
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            self.set_api_key(api_key)

    def set_api_key(self, api_key: str) -> bool:
        if not api_key:
            return False
        try:
            genai.configure(api_key=api_key)
            self.api_key = api_key
            return True
        except Exception as e:
            print(f"Error configuring Gemini API: {e}")
            return False

    def is_api_configured(self) -> bool:
        """True if the current model doesn't need a key, or if a Gemini key is set."""
        if self.is_model_ollama():
            return True  # local model, always ready
        return self.api_key is not None and len(self.api_key.strip()) > 0

    # ------------------------------------------------------------------
    # Chroma / Index helpers
    # ------------------------------------------------------------------

    def get_chunk_count(self) -> int:
        try:
            if self.collection:
                return self.collection.count()
        except Exception:
            pass
        return 0

    def extract_text(self, file_path: str) -> str:
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
        text = re.sub(r'\s+', ' ', text).strip()
        chunks = []
        start = 0
        text_len = len(text)
        chunk_idx = 0
        while start < text_len:
            end = min(start + CHUNK_SIZE, text_len)
            if end < text_len:
                boundary = -1
                for char in ['. ', '? ', '! ', ' ']:
                    r_idx = text.rfind(char, start + CHUNK_SIZE - 100, end)
                    if r_idx != -1:
                        boundary = max(boundary, r_idx + len(char))
                if boundary != -1:
                    end = boundary
            chunk_text_val = text[start:end].strip()
            if chunk_text_val:
                chunks.append({
                    "id": f"{filename}_chunk_{chunk_idx}",
                    "filename": filename,
                    "chunk_index": chunk_idx,
                    "text": chunk_text_val
                })
                chunk_idx += 1
            start = end - CHUNK_OVERLAP
            if start >= text_len or end >= text_len:
                break
        return chunks

    def add_document(self, file_path: str) -> Dict[str, Any]:
        if not self.collection:
            return {"status": "error", "message": "Chroma DB not available."}
        filename = os.path.basename(file_path)
        self.delete_document(filename)
        print(f"Processing document: {filename}")
        text = self.extract_text(file_path)
        chunks = self.chunk_text(text, filename)
        if not chunks:
            return {"status": "success", "chunks_count": 0, "message": "Document was empty."}
        print(f"Split into {len(chunks)} chunks. Generating embeddings...")
        texts_to_embed = [c["text"] for c in chunks]
        embeddings = self.embedding_model.encode(texts_to_embed, show_progress_bar=False).tolist()
        ids = [chunk["id"] for chunk in chunks]
        metadatas = [{"source": chunk["filename"], "title": chunk["filename"], "chunk_index": chunk["chunk_index"]} for chunk in chunks]
        documents = [chunk["text"] for chunk in chunks]
        print("Writing to Chroma DB...")
        self.collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
        return {"status": "success", "chunks_count": len(chunks), "message": f"Successfully indexed {filename}."}

    def delete_document(self, filename: str) -> bool:
        if not self.collection:
            return False
        try:
            res = self.collection.get(where={"source": filename})
            deleted_count = len(res["ids"]) if res and "ids" in res else 0
            if deleted_count > 0:
                self.collection.delete(where={"source": filename})
            for search_dir in [DATA_DIR, "./sandbox/cci_notes"]:
                path = os.path.join(search_dir, filename)
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception as e:
                        print(f"Error removing file {filename}: {e}")
            return deleted_count > 0
        except Exception as e:
            print(f"Error deleting document from Chroma: {e}")
            return False

    def get_indexed_documents(self) -> List[Dict[str, Any]]:
        if not self.collection:
            return []
        try:
            res = self.collection.get(include=["metadatas"])
            docs = {}
            for meta in res.get("metadatas", []):
                fname = meta.get("source")
                if fname:
                    if fname not in docs:
                        file_path = os.path.join(DATA_DIR, fname)
                        if not os.path.exists(file_path):
                            file_path = os.path.join("./sandbox/cci_notes", fname)
                        size_bytes = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                        docs[fname] = {"filename": fname, "chunks": 0, "size_bytes": size_bytes}
                    docs[fname]["chunks"] += 1
            return list(docs.values())
        except Exception as e:
            print(f"Error getting documents: {e}")
            return []

    def search_similar_chunks(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        if not self.collection:
            return []
        try:
            query_embedding = self.embedding_model.encode([query]).tolist()
            results = self.collection.query(query_embeddings=query_embedding, n_results=top_k)
            formatted = []
            if results and "documents" in results and results["documents"] and len(results["documents"][0]) > 0:
                docs = results["documents"][0]
                metas = results["metadatas"][0]
                distances = results.get("distances", [[]])[0]
                for idx, (doc, meta) in enumerate(zip(docs, metas)):
                    dist = distances[idx] if idx < len(distances) else 0.5
                    similarity = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
                    formatted.append({
                        "id": f"{meta.get('source')}_chunk_{meta.get('chunk_index')}",
                        "filename": meta.get("source", "Unknown"),
                        "text": doc,
                        "similarity": similarity
                    })
            return formatted
        except Exception as e:
            print(f"Error searching chunks: {e}")
            return []

    # ------------------------------------------------------------------
    # Generation — routes to Gemini or Ollama
    # ------------------------------------------------------------------

    def generate_response(self, query: str, contexts: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
        if not contexts:
            return (
                "I couldn't find any relevant information in the knowledge base. "
                "Please upload conservation documents first, or refine your query.",
                []
            )

        context_str = ""
        for i, ctx in enumerate(contexts):
            context_str += f"Source [{i+1}] ({ctx['filename']}):\n{ctx['text']}\n\n"

        prompt = f"""You are an Artwork Damage Restoration Assistant and world-class conservation expert.
Provide professional, clear, and actionable advice to restorers and conservationists.

CRITICAL INSTRUCTION: Answer STRICTLY from the provided context sources.
- Do NOT make up facts or use external knowledge.
- If context is insufficient, say so clearly.
- Cite sources as [Source 1], [Source 2], etc.

---
RELEVANT KNOWLEDGE CONTEXT:
{context_str}
---

USER QUESTION:
{query}

ARTWORK DAMAGE RESTORATION ASSISTANT RESPONSE:"""

        model_id = self.selected_model

        if self.is_model_ollama(model_id):
            return self._generate_with_ollama(prompt, model_id, contexts)
        else:
            return self._generate_with_gemini(prompt, model_id, contexts)

    def _generate_with_gemini(self, prompt: str, model_id: str, contexts: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
        if not self.api_key:
            mock = (
                f"[MOCK MODE — Gemini API Key Not Set]\n\n"
                f"Model selected: **{model_id}**\n\n"
                "To get a real answer, please set your Gemini API key in Settings.\n\n"
                "**Retrieved sources:**\n"
            )
            for i, ctx in enumerate(contexts):
                mock += f"- **[Source {i+1}] {ctx['filename']}:** \"{ctx['text'][:150]}...\"\n\n"
            return mock, contexts
        try:
            model = genai.GenerativeModel(f"models/{model_id}")
            response = model.generate_content(prompt)
            return response.text, contexts
        except Exception as e:
            return f"Error generating answer with Gemini ({model_id}): {e}", contexts

    def _generate_with_ollama(self, prompt: str, model_id: str, contexts: List[Dict[str, Any]], _retry: bool = False) -> Tuple[str, List[Dict[str, Any]]]:
        """Calls Ollama REST API with GPU acceleration when available."""
        # --- Compute GPU layers dynamically ---
        gpu = get_gpu_info()
        if gpu["available"]:
            num_gpu = compute_num_gpu_layers(model_id, gpu["vram_free_mb"])
            gpu_label = f"GPU ({gpu['name']}, {gpu['vram_free_mb']} MB free) — {num_gpu} layers"
        else:
            num_gpu = 0
            gpu_label = "CPU only (no GPU detected)"

        print(f"[Ollama] Running '{model_id}' | Backend: {gpu_label}")

        payload = {
            "model": model_id,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_gpu": num_gpu,   # 0 = CPU, 99 = all layers on GPU
                "temperature": 0.3,
                "num_predict": 1024,
                "num_thread": os.cpu_count() or 4,  # use all CPU cores as fallback
            }
        }

        try:
            resp = http_requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=payload,
                timeout=180,  # longer timeout for GPU warmup on first run
            )
            if resp.status_code == 200:
                data = resp.json()
                answer = data.get("response", "").strip()

                # Append performance footnote
                eval_count = data.get("eval_count", 0)
                eval_dur_s = data.get("eval_duration", 0) / 1e9
                tok_per_sec = round(eval_count / eval_dur_s, 1) if eval_dur_s > 0 else 0
                backend_note = (
                    f"\n\n---\n*🖥️ Local model: `{model_id}` | "
                    f"Backend: {gpu_label} | "
                    f"{tok_per_sec} tok/s*"
                )
                return answer + backend_note, contexts

            else:
                # Auto-pull if model is missing
                if resp.status_code == 404 or "not found" in resp.text.lower():
                    if not _retry:
                        print(f"[Ollama] Model '{model_id}' not found locally. Pulling now...")
                        pull_result = pull_ollama_model(model_id)
                        if pull_result["success"]:
                            return self._generate_with_ollama(prompt, model_id, contexts, _retry=True)
                    return (
                        f"⚠️ Ollama model `{model_id}` is not installed and could not be downloaded automatically. "
                        f"Run `ollama pull {model_id}` in a terminal to install it.",
                        contexts
                    )
                return f"Ollama returned HTTP {resp.status_code}: {resp.text[:300]}", contexts

        except http_requests.exceptions.ConnectionError:
            return (
                "⚠️ **Ollama is not running.** Start it by running:\n```\nollama serve\n```\nthen refresh and try again.",
                contexts
            )
        except Exception as e:
            return f"Error generating answer with Ollama ({model_id}): {e}", contexts
