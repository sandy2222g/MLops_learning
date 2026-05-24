from flask import Flask, request, jsonify
from flask_cors import CORS
import util
import io

app = Flask(__name__)
CORS(app)

@app.route('/get_column_names', methods=['GET'])
def get_column_names():
    response = jsonify({
        'columns': util.get_column_names()
    })
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/predict_restoration', methods=['POST'])
def predict_restoration():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        img_bytes = file.read()
        
        # 1. Get base features for UI display
        base_features = util.extract_features_from_image(img_bytes)
        if base_features is None:
            return jsonify({'error': 'Failed to process image'}), 500
            
        # 2. Get the prediction (this handles engineering & scaling internally)
        prediction = util.get_prediction(img_bytes)
        
        # 3. Combine base feature names with their values for a neat UI list
        column_names = util.get_column_names()
        feature_list = []
        for name, value in zip(column_names, base_features):
            feature_list.append({
                'name': name.replace('_', ' ').title(),
                'value': round(float(value), 4) if isinstance(value, (int, float, np.float64, np.float32)) else value
            })

        response = jsonify({
            'prediction': prediction,
            'features': feature_list,
            'status': 'success'
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    import numpy as np # Needed for type checking in the loop
    print("Starting Python Flask Server For Art Restoration Prediction...")
    util.load_saved_artifacts()
    app.run(port=5000, debug=True)
