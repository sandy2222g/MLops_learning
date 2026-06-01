import os
import time
import torch
import cv2
from flask import Flask, render_template, request, jsonify, url_for
from werkzeug.utils import secure_filename
from ultralytics import YOLO

app = Flask(__name__)

# Folder Configuration
UPLOAD_FOLDER = os.path.join('static', 'uploads')
IMAGE_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'images')
VIDEO_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'videos')

os.makedirs(IMAGE_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(VIDEO_UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload size

# Model Paths
MODELS = {
    'medium': os.path.abspath(os.path.join(os.path.dirname(__file__), 'model', 'best.pt')),
    'nano': os.path.abspath(os.path.join(os.path.dirname(__file__), 'model', 'nano.pt'))
}

# Cache loaded models
loaded_models = {}

def get_model(model_type='medium'):
    """Loads and caches the requested YOLOv11 model."""
    if model_type not in MODELS:
        model_type = 'medium'
    
    if model_type not in loaded_models:
        model_path = MODELS[model_type]
        if os.path.exists(model_path):
            print(f"Loading YOLO model weights from: {model_path}")
            # Load model onto CPU or GPU depending on availability
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            loaded_models[model_type] = YOLO(model_path).to(device)
        else:
            print(f"ERROR: Model weights not found at {model_path}!")
            return None
    return loaded_models[model_type]

# Smart City Recommendations based on flood level
RECOMMENDATIONS = {
    'safe': {
        'status': 'Safe (Normal Conditions)',
        'alert_class': 'status-safe',
        'badge': 'Safe',
        'icon': 'bi-shield-check',
        'color': '#10b981',
        'desc': 'No current flooding or water accumulation detected on roadways.',
        'actions': [
            'Normal city operations continue.',
            'Regular storm drain maintenance should be scheduled.',
            'No public alerts required.'
        ]
    },
    'warning': {
        'status': 'Warning (Minor Flooding / Water Accumulation)',
        'alert_class': 'status-warning',
        'badge': 'Warning',
        'icon': 'bi-exclamation-triangle',
        'color': '#f59e0b',
        'desc': 'Moderate water levels or rising water detected. Potential road obstruction.',
        'actions': [
            'Alert local drainage maintenance and smart city control center.',
            'Display cautionary messages on Dynamic Message Signs (DMS).',
            'Advise residents to avoid low-lying street crossings.'
        ]
    },
    'danger': {
        'status': 'Danger (Severe Flooding / Flash Flood)',
        'alert_class': 'status-danger',
        'badge': 'Danger',
        'icon': 'bi-exclamation-octagon',
        'color': '#ef4444',
        'desc': 'Severe flooding detected. High-water levels pose threat to vehicles and pedestrians.',
        'actions': [
            'Trigger automatic road closures and dispatch emergency barrier systems.',
            'Broadcast emergency mobile alerts to residents in high-risk zones.',
            'Activate emergency water pumps and redirect smart traffic systems.'
        ]
    }
}

# In-memory prediction history
prediction_history = []

@app.route('/')
def index():
    """Renders the main single-page application dashboard."""
    # Ensure standard model is loaded initially
    get_model('medium')
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    """API endpoint to run YOLOv11 classification on an uploaded image."""
    try:
        model_type = request.form.get('model_type', 'medium')
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Empty filename'}), 400
        
        # Save image
        filename = secure_filename(f"{int(time.time())}_{file.filename}")
        filepath = os.path.join(IMAGE_UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        model = get_model(model_type)
        if not model:
            return jsonify({'success': False, 'error': f"Model weight '{model_type}' not loaded"}), 500
        
        # Run inference and measure time
        start_time = time.time()
        results = model(filepath, verbose=False)
        inference_ms = round((time.time() - start_time) * 1000, 2)
        
        # Parse prediction results
        probs = results[0].probs
        top1_idx = probs.top1
        top1_conf = float(probs.top1conf)
        top1_name = model.names[top1_idx].lower()
        
        # Map output names to danger/warning/safe (in case of uppercase/lowercase variants)
        if top1_name not in ['safe', 'warning', 'danger']:
            # Fallback mappings if class names differ slightly
            if 'danger' in top1_name:
                top1_name = 'danger'
            elif 'warning' in top1_name:
                top1_name = 'warning'
            else:
                top1_name = 'safe'
        
        # Retrieve complete probabilities mapping
        class_probabilities = {}
        for idx, val in enumerate(probs.data):
            c_name = model.names[idx].lower()
            if c_name in ['safe', 'warning', 'danger']:
                class_probabilities[c_name] = float(val)
        
        # Fill missing classes if any
        for key in ['safe', 'warning', 'danger']:
            if key not in class_probabilities:
                class_probabilities[key] = 0.0

        recommendation = RECOMMENDATIONS.get(top1_name, RECOMMENDATIONS['safe'])
        
        # Save to local in-memory history
        image_url = url_for('static', filename=f"uploads/images/{filename}")
        history_item = {
            'id': len(prediction_history) + 1,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'filename': file.filename,
            'file_url': image_url,
            'type': 'image',
            'model_used': model_type,
            'result': top1_name,
            'confidence': top1_conf,
            'inference_ms': inference_ms
        }
        prediction_history.insert(0, history_item) # Insert at front
        
        return jsonify({
            'success': True,
            'result': top1_name,
            'confidence': top1_conf,
            'probabilities': class_probabilities,
            'inference_ms': inference_ms,
            'file_url': image_url,
            'recommendations': recommendation
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f"Internal Server Error: {str(e)}"}), 500

@app.route('/predict_video', methods=['POST'])
def predict_video():
    """API endpoint to run downsampled frame-by-frame YOLOv11 classification on a video."""
    try:
        model_type = request.form.get('model_type', 'medium')
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Empty filename'}), 400
        
        # Save video
        filename = secure_filename(f"{int(time.time())}_{file.filename}")
        filepath = os.path.join(VIDEO_UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        model = get_model(model_type)
        if not model:
            return jsonify({'success': False, 'error': f"Model weight '{model_type}' not loaded"}), 500
        
        # Open video and get properties
        cap = cv2.VideoCapture(filepath)
        if not cap.isOpened():
            return jsonify({'success': False, 'error': 'Could not open video file'}), 400
        
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = round(total_frames / fps, 2)
        
        # We will process 2 frames per second of the video to optimize speed
        # If video is 30 FPS, skip_interval = 15. We analyze frame 0, 15, 30, etc.
        skip_interval = max(1, int(fps / 2))
        
        timeline = []
        frame_idx = 0
        processed_count = 0
        total_inference_time = 0
        
        class_counts = {'safe': 0, 'warning': 0, 'danger': 0}
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % skip_interval == 0:
                start_inference = time.time()
                results = model(frame, verbose=False)
                inference_ms = (time.time() - start_inference) * 1000
                total_inference_time += inference_ms
                
                probs = results[0].probs
                top1_idx = probs.top1
                top1_conf = float(probs.top1conf)
                top1_name = model.names[top1_idx].lower()
                
                if top1_name not in ['safe', 'warning', 'danger']:
                    if 'danger' in top1_name:
                        top1_name = 'danger'
                    elif 'warning' in top1_name:
                        top1_name = 'warning'
                    else:
                        top1_name = 'safe'
                
                class_counts[top1_name] += 1
                
                all_probs = {}
                for idx, val in enumerate(probs.data):
                    c_name = model.names[idx].lower()
                    if c_name in ['safe', 'warning', 'danger']:
                        all_probs[c_name] = float(val)
                
                # Fill missing classes
                for key in ['safe', 'warning', 'danger']:
                    if key not in all_probs:
                        all_probs[key] = 0.0

                timestamp = round(frame_idx / fps, 2)
                timeline.append({
                    'time': timestamp,
                    'class': top1_name,
                    'confidence': top1_conf,
                    'probabilities': all_probs
                })
                processed_count += 1
                
            frame_idx += 1
            
        cap.release()
        
        if processed_count == 0:
            return jsonify({'success': False, 'error': 'No video frames were processed'}), 400
        
        # Calculate overall hazard score based on priority and frequency
        # If danger is present in >= 10% of frames (or at least 2 frames), mark as danger
        danger_pct = class_counts['danger'] / processed_count
        warning_pct = class_counts['warning'] / processed_count
        
        if class_counts['danger'] >= 2 or danger_pct >= 0.10:
            overall_result = 'danger'
        elif class_counts['warning'] >= 2 or warning_pct >= 0.10:
            overall_result = 'warning'
        else:
            overall_result = 'safe'
            
        avg_inference_ms = round(total_inference_time / processed_count, 2)
        recommendation = RECOMMENDATIONS.get(overall_result, RECOMMENDATIONS['safe'])
        video_url = url_for('static', filename=f"uploads/videos/{filename}")
        
        # Save to history
        history_item = {
            'id': len(prediction_history) + 1,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'filename': file.filename,
            'file_url': video_url,
            'type': 'video',
            'model_used': model_type,
            'result': overall_result,
            'confidence': max([t['confidence'] for t in timeline if t['class'] == overall_result] or [0.0]),
            'inference_ms': avg_inference_ms
        }
        prediction_history.insert(0, history_item)
        
        return jsonify({
            'success': True,
            'result': overall_result,
            'duration_sec': duration,
            'total_frames': total_frames,
            'processed_frames': processed_count,
            'timeline': timeline,
            'class_counts': class_counts,
            'inference_ms': avg_inference_ms,
            'file_url': video_url,
            'recommendations': recommendation
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f"Internal Server Error: {str(e)}"}), 500

@app.route('/system_status', methods=['GET'])
def system_status():
    """GET endpoint to return model parameters and hardware status."""
    try:
        model_type = request.args.get('model_type', 'medium')
        model = get_model(model_type)
        
        device_name = "CPU"
        if torch.cuda.is_available():
            device_name = f"GPU: {torch.cuda.get_device_name(0)}"
            
        weights_size_mb = 20.8 if model_type == 'medium' else 5.2
        
        if model:
            num_classes = len(model.names)
            classes = list(model.names.values())
        else:
            num_classes = 3
            classes = ['danger', 'warning', 'safe']
            
        return jsonify({
            'success': True,
            'hardware': device_name,
            'cuda_available': torch.cuda.is_available(),
            'model_type': model_type,
            'model_classes': classes,
            'num_classes': num_classes,
            'weights_size_mb': weights_size_mb,
            'inference_type': 'FP32'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/history', methods=['GET'])
def get_history():
    """GET endpoint to return prediction logs."""
    return jsonify({
        'success': True,
        'history': prediction_history
    })

if __name__ == '__main__':
    print("Starting Smart City Flood Classifier Flask Server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)
