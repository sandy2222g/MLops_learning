# SECTION: IMPORTS AND DEPENDENCIES
# Description: This section loads all external libraries and internal helper modules required to run the server.

import os
import sys
import flask
import flask.json
from flask import Flask, request, jsonify
from flask_cors import CORS
import util
import numpy as np
import traceback
import base64
import shutil

# Add the rag directory to path so we can import rag_engine
RAG_DIR = os.path.join(os.path.dirname(__file__), '..', 'rag')
sys.path.insert(0, os.path.abspath(RAG_DIR))


# SECTION: CUSTOM JSON SERIALIZATION
# Description: Standard JSON library cannot serialize numpy types. This provider handles numpy types to avoid 500 errors.

class NumpyJSONProvider(flask.json.provider.DefaultJSONProvider):
    """Custom JSON provider that converts Numpy numbers and arrays to native Python types."""
    def default(self, o):
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return super().default(o)


# SECTION: APPLICATION INITIALIZATION
# Description: Configures the Flask application instance, custom JSON encoder, and allows cross-origin requests.

app = Flask(__name__)
app.json = NumpyJSONProvider(app)
CORS(app)


# SECTION: YOLO MODEL INITIALIZATION
# Description: Loads the YOLO segmentation model once at startup for crack damage detection.

_yolo_model = None

def get_yolo_model():
    """Lazy-loads the YOLO model on first use."""
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            weights_path = os.path.join(
                os.path.dirname(__file__), '..', 'yolomodel artwork',
                'runs', 'segment', 'train-4', 'weights', 'best.pt'
            )
            _yolo_model = YOLO(os.path.abspath(weights_path))
            print("YOLO model loaded successfully.")
        except Exception as e:
            print(f"Failed to load YOLO model: {e}")
            _yolo_model = None
    return _yolo_model


# SECTION: RAG ENGINE INITIALIZATION
# Description: Initializes the RAG engine pointing to the rag/ folder's ChromaDB and data directory.

_rag_engine = None

def get_rag_engine():
    """Lazy-loads the RAG engine on first use."""
    global _rag_engine
    if _rag_engine is None:
        try:
            # Load .env from the rag directory for the Gemini API key
            from dotenv import load_dotenv
            env_path = os.path.join(RAG_DIR, '.env')
            load_dotenv(dotenv_path=env_path)

            from rag_engine import RAGEngine, DATA_DIR, CHROMA_DIR

            # Override paths to point at the rag/ subdirectory
            import rag_engine as _re
            _re.DATA_DIR = os.path.join(RAG_DIR, 'data')
            _re.CHROMA_DIR = os.path.join(RAG_DIR, 'sandbox', 'chroma_db')
            os.makedirs(_re.DATA_DIR, exist_ok=True)

            _rag_engine = RAGEngine()
            print("RAG engine initialized.")
        except Exception as e:
            print(f"Failed to initialize RAG engine: {e}")
            traceback.print_exc()
            _rag_engine = None
    return _rag_engine


# SECTION: ENDPOINT - GET COLUMN NAMES
# Description: Returns the list of base features the model expects.

@app.route('/get_column_names', methods=['GET'])
def get_column_names():
    return jsonify({'columns': util.get_column_names()})


# SECTION: ENDPOINT - PREDICT ART RESTORATION DIFFICULTY
# Description: Receives uploaded image, runs extraction and engineering, and returns restoration classification.

@app.route('/predict_restoration', methods=['POST'])
def predict_restoration():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        img_bytes = file.read()

        base_features = util.extract_features_from_image(img_bytes)
        if base_features is None:
            return jsonify({'error': 'Failed to process image'}), 500

        prediction = util.get_prediction(img_bytes)

        column_names = util.get_column_names()
        feature_list = [
            {'name': name.replace('_', ' ').title(), 'value': value}
            for name, value in zip(column_names, base_features)
        ]

        return jsonify({
            'prediction': prediction,
            'features': feature_list,
            'status': 'success'
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# SECTION: ENDPOINT - DAMAGE DETECTION (YOLO)
# Description: Receives an image, runs YOLO segmentation to detect cracks, returns annotated image + stats.

@app.route('/detect_damage', methods=['POST'])
def detect_damage():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        model = get_yolo_model()
        if model is None:
            return jsonify({'error': 'YOLO model not available'}), 500

        import cv2

        img_bytes = file.read()
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({'error': 'Failed to decode image'}), 400

        results = model(img, verbose=False)
        result = results[0]

        crack_count = 0
        avg_confidence = 0.0
        coverage_pct = 0.0
        annotated_b64 = None

        if result.boxes is not None and len(result.boxes) > 0:
            crack_count = len(result.boxes)
            confidences = result.boxes.conf.cpu().numpy()
            avg_confidence = float(np.mean(confidences)) * 100

            # Calculate mask coverage if segmentation masks exist
            if result.masks is not None:
                total_pixels = img.shape[0] * img.shape[1]
                mask_union = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
                for mask in result.masks.data.cpu().numpy():
                    # Resize mask to image size if needed
                    mask_resized = cv2.resize(mask, (img.shape[1], img.shape[0]))
                    mask_union = np.maximum(mask_union, (mask_resized > 0.5).astype(np.uint8))
                coverage_pct = float(np.sum(mask_union) / total_pixels) * 100

        # Get annotated image from YOLO
        annotated_img = result.plot()
        _, buffer = cv2.imencode('.jpg', annotated_img)
        annotated_b64 = base64.b64encode(buffer).decode('utf-8')

        return jsonify({
            'crack_count': crack_count,
            'avg_confidence': round(avg_confidence, 1),
            'coverage_pct': round(coverage_pct, 2),
            'annotated_image': annotated_b64,
            'status': 'success'
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# SECTION: RAG BOT ENDPOINTS
# Description: Routes for the RAG chatbot — querying, status, settings, model listing, and document management.

@app.route('/rag/status', methods=['GET'])
def rag_status():
    engine = get_rag_engine()
    if engine is None:
        return jsonify({'error': 'RAG engine not available'}), 500
    gpu = engine.get_gpu_status()
    return jsonify({
        'api_key_configured': engine.is_api_configured(),
        'chunk_count': engine.get_chunk_count(),
        'selected_model': engine.get_selected_model(),
        'gpu_available': gpu.get('available', False),
        'gpu_name': gpu.get('name', None),
    })


@app.route('/rag/models', methods=['GET'])
def rag_models():
    engine = get_rag_engine()
    if engine is None:
        return jsonify({'error': 'RAG engine not available'}), 500
    return jsonify(engine.get_supported_models())


@app.route('/rag/settings', methods=['POST'])
def rag_settings():
    engine = get_rag_engine()
    if engine is None:
        return jsonify({'error': 'RAG engine not available'}), 500

    data = request.get_json(force=True) or {}
    results = {}

    model_id = data.get('model_id')
    if model_id:
        ok = engine.set_model(model_id)
        if not ok:
            return jsonify({'error': f"Unknown model id: '{model_id}'"}), 400
        results['model'] = model_id

    api_key = data.get('api_key')
    if api_key:
        success = engine.set_api_key(api_key)
        if not success:
            return jsonify({'error': 'Invalid Gemini API Key.'}), 400
        try:
            env_path = os.path.join(RAG_DIR, '.env')
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write(f'GEMINI_API_KEY={api_key}\n')
        except Exception as e:
            print(f"Error saving API key: {e}")
        results['api_key'] = 'updated'

    if not results:
        return jsonify({'error': 'No settings provided.'}), 400

    return jsonify({'status': 'success', 'updated': results, 'selected_model': engine.get_selected_model()})


@app.route('/rag/query', methods=['POST'])
def rag_query():
    engine = get_rag_engine()
    if engine is None:
        return jsonify({'error': 'RAG engine not available'}), 500
    try:
        data = request.get_json(force=True) or {}
        query = data.get('query', '').strip()
        if not query:
            return jsonify({'error': 'Query cannot be empty'}), 400

        contexts = engine.search_similar_chunks(query, top_k=4)
        answer, sources = engine.generate_response(query, contexts)
        return jsonify({
            'answer': answer,
            'sources': [{'filename': s.get('filename', ''), 'text': s.get('text', '')[:200]} for s in sources],
            'model_used': engine.get_selected_model(),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/rag/documents', methods=['GET'])
def rag_documents():
    engine = get_rag_engine()
    if engine is None:
        return jsonify({'error': 'RAG engine not available'}), 500
    return jsonify(engine.get_indexed_documents())


@app.route('/rag/documents/<filename>', methods=['DELETE'])
def rag_delete_document(filename):
    engine = get_rag_engine()
    if engine is None:
        return jsonify({'error': 'RAG engine not available'}), 500
    deleted = engine.delete_document(filename)
    if not deleted:
        return jsonify({'error': f"Document '{filename}' not found."}), 404
    return jsonify({'status': 'success', 'message': f'Successfully deleted {filename}.'})


@app.route('/rag/upload', methods=['POST'])
def rag_upload():
    engine = get_rag_engine()
    if engine is None:
        return jsonify({'error': 'RAG engine not available'}), 500
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        filename = file.filename or ''
        if not filename:
            return jsonify({'error': 'No filename provided.'}), 400
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ['.txt', '.pdf', '.docx']:
            return jsonify({'error': 'Unsupported format. Use TXT, PDF, or DOCX.'}), 400

        import rag_engine as _re
        data_dir = _re.DATA_DIR
        file_path = os.path.join(data_dir, filename)
        with open(file_path, 'wb') as buf:
            shutil.copyfileobj(file.stream, buf)

        result = engine.add_document(file_path)
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# SECTION: ARTIFACTS LOADING & APPLICATION STARTUP
# Description: Loads machine learning model and normalizer before binding the port.

util.load_saved_artifacts()

if __name__ == "__main__":
    print("Starting Flask Server For Art Restoration Prediction...")
    app.run(port=5000, debug=True)
