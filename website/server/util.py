import joblib
import json
import numpy as np
import pandas as pd
import os
import cv2
from sklearn.preprocessing import StandardScaler
from skimage import feature, measure, segmentation, color, filters

__model = None
__columns = None
__scaler = None

def extract_features_from_image(image_bytes):
    """
    Extracts the 15 base features from an image's bytes.
    Matches the columns in art_restoration_dataset_new.csv
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return None

    # Convert to grayscale for some features
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 1. blur_score (Laplacian variance)
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    # 2. brightness
    brightness = np.mean(gray)
    
    # 3. contrast
    contrast = gray.std()
    
    # 4. edge_count
    edges = cv2.Canny(gray, 100, 200)
    edge_count = np.count_nonzero(edges)
    
    # 5. noise_level (Approximated by standard deviation of a local neighborhood)
    noise_level = cv2.meanStdDev(gray)[1][0][0] # Simple std dev as proxy
    
    # 6. entropy
    entropy = measure.shannon_entropy(gray)
    
    # 7. saturation
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    saturation = np.mean(hsv[:, :, 1])
    
    # 8. sharpness (Matches blur_score in your dataset)
    sharpness = blur_score
    
    # 9. dark_ratio (Pixels below threshold)
    dark_ratio = np.count_nonzero(gray < 30) / gray.size
    
    # 10. white_ratio (Pixels above threshold)
    white_ratio = np.count_nonzero(gray > 225) / gray.size
    
    # 11. contour_count
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour_count = len(contours)
    
    # 12. width & 13. height
    height, width = img.shape[:2]
    
    # 14. aspect_ratio
    aspect_ratio = width / height
    
    # 15. mean colors (BGR in OpenCV)
    mean_blue, mean_green, mean_red = cv2.mean(img)[:3]
    
    return [
        blur_score, brightness, contrast, edge_count, noise_level,
        entropy, saturation, sharpness, dark_ratio, white_ratio,
        contour_count, width, height, aspect_ratio,
        mean_red, mean_green, mean_blue
    ]

def get_prediction(image_bytes):
    """
    Extracts features from image bytes, engineers more, and predicts.
    """
    base_features = extract_features_from_image(image_bytes)
    if base_features is None:
        return None
    
    if __model is None or __scaler is None:
        return None
    
    try:
        # Create a dict for engineering
        data = dict(zip(__columns, base_features))
        
        # Engineering (matching the notebook)
        data['degradation_score'] = ((data['noise_level'] * 0.3) + (data['dark_ratio'] * 100) + 
                                    (data['white_ratio'] * 100) + (data['edge_count'] * 0.002) + 
                                    (data['contrast'] * 0.2))
        data['visual_quality_score'] = ((data['sharpness'] * 0.4) + (data['brightness'] * 0.2) + 
                                       (data['saturation'] * 0.2) + (data['entropy'] * 5))
        data['texture_complexity'] = ((data['entropy'] * 10) + (data['contour_count'] * 0.5))
        data['color_richness'] = (data['mean_red'] + data['mean_green'] + data['mean_blue']) / 3
        data['crack_intensity'] = ((data['white_ratio'] * 100) + (data['edge_count'] * 0.001))
        data['blur_intensity'] = (1000 / (data['blur_score'] + 1))
        
        final_feature_order = [
            'blur_score', 'brightness', 'contrast', 'edge_count', 'noise_level',
            'entropy', 'saturation', 'sharpness', 'dark_ratio', 'white_ratio',
            'contour_count', 'aspect_ratio', 'mean_red', 'mean_green', 'mean_blue',
            'degradation_score', 'visual_quality_score', 'texture_complexity',
            'color_richness', 'crack_intensity', 'blur_intensity'
        ]
        
        final_features = [data[f] for f in final_feature_order]
        
        # Scale and Predict
        x = np.array(final_features).reshape(1, -1)
        x_scaled = __scaler.transform(x)
        prediction = __model.predict(x_scaled)[0]
        
        class_map = {0: "Easy", 1: "Moderate", 2: "Difficult", 3: "Impossible"}
        return class_map.get(prediction, str(prediction))
        
    except Exception as e:
        print(f"Error during prediction: {e}")
        return None

def load_saved_artifacts():
    print("Loading saved artifacts...start")
    global __model, __columns, __scaler

    # Load Columns
    column_path = os.path.join(os.path.dirname(__file__), "artifacts", "column.json")
    with open(column_path, "r") as f:
        __columns = json.load(f)['columns']

    # Load Model
    model_path = os.path.join(os.path.dirname(__file__), "artifacts", "art_restoration_model.pkl")
    __model = joblib.load(model_path)

    # Load Dataset and fit Scaler
    # For Docker compatibility, we check /model first, then fallback to relative path
    dataset_path = "/model/art_restoration_dataset_new.csv"
    if not os.path.exists(dataset_path):
        dataset_path = os.path.join(os.path.dirname(__file__), "..", "model", "art_restoration_dataset_new.csv")
    
    df = pd.read_csv(dataset_path)
    
    # Feature Engineering for scaler
    df['degradation_score'] = ((df['noise_level'] * 0.3) + (df['dark_ratio'] * 100) + 
                                (df['white_ratio'] * 100) + (df['edge_count'] * 0.002) + 
                                (df['contrast'] * 0.2))
    df['visual_quality_score'] = ((df['sharpness'] * 0.4) + (df['brightness'] * 0.2) + 
                                    (df['saturation'] * 0.2) + (df['entropy'] * 5))
    df['texture_complexity'] = ((df['entropy'] * 10) + (df['contour_count'] * 0.5))
    df['color_richness'] = (df['mean_red'] + df['mean_green'] + df['mean_blue']) / 3
    df['crack_intensity'] = ((df['white_ratio'] * 100) + (df['edge_count'] * 0.001))
    df['blur_intensity'] = (1000 / (df['blur_score'] + 1))
    
    final_feature_order = [
        'blur_score', 'brightness', 'contrast', 'edge_count', 'noise_level',
        'entropy', 'saturation', 'sharpness', 'dark_ratio', 'white_ratio',
        'contour_count', 'aspect_ratio', 'mean_red', 'mean_green', 'mean_blue',
        'degradation_score', 'visual_quality_score', 'texture_complexity',
        'color_richness', 'crack_intensity', 'blur_intensity'
    ]
    
    X = df[final_feature_order]
    __scaler = StandardScaler()
    __scaler.fit(X)
    print("Artifacts loaded and scaler fitted.")

def get_column_names():
    return __columns

if __name__ == "__main__":
    load_saved_artifacts()
