from flask import Flask, request, jsonify
from flask_cors import CORS
import util
import io
import numpy as np
import traceback
import json

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.int64, np.int32, np.integer)):
            return int(obj)
        if isinstance(obj, (np.float64, np.float32, np.floating)):
            return float(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

app = Flask(__name__)
app.json_encoder = NumpyEncoder # For older Flask
# For newer Flask:
class UpdatedJSONProvider(flask.json.provider.DefaultJSONProvider):
    def default(self, o):
        if isinstance(o, (np.int64, np.int32, np.integer)):
            return int(o)
        if isinstance(o, (np.float64, np.float32, np.floating)):
            return float(o)
        if isinstance(o, (np.ndarray,)):
            return o.tolist()
        return super().default(o)

import flask.json
app.json = UpdatedJSONProvider(app)

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
        print("Processing analysis request - v2.0-JSON-FIX") # Verification marker
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
            
        # 2. Get the prediction
        prediction = util.get_prediction(img_bytes)
        
        # 3. Combine base feature names with their values
        column_names = util.get_column_names()
        feature_list = []
        for name, value in zip(column_names, base_features):
            feature_list.append({
                'name': name.replace('_', ' ').title(),
                'value': value
            })

        return jsonify({
            'prediction': prediction,
            'features': feature_list,
            'status': 'success'
        })
        
    except Exception as e:
        print("!!! SERVER ERROR !!!")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

util.load_saved_artifacts()

if __name__ == "__main__":
    print("Starting Python Flask Server For Art Restoration Prediction...")
    app.run(port=5000, debug=True)
