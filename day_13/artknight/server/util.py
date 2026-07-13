# SECTION: IMPORTS AND DEPENDENCIES
# Description: Imports core data science, image processing, and machine learning utilities.

import joblib
import json
import numpy as np
import pandas as pd
import os
import cv2
from sklearn.preprocessing import StandardScaler
from skimage import measure


# SECTION: GLOBAL VARIABLES AND CONFIGURATIONS
# Description: Stores the shared state for the loaded ML model, expected columns list, and fitted normalizer.

__model = None
__columns = None
__scaler = None

FEATURE_ORDER = [
    'blur_score', 'brightness', 'contrast', 'edge_count', 'noise_level',
    'entropy', 'saturation', 'sharpness', 'dark_ratio', 'white_ratio',
    'contour_count', 'aspect_ratio', 'mean_red', 'mean_green', 'mean_blue',
    'degradation_score', 'visual_quality_score', 'texture_complexity',
    'color_richness', 'crack_intensity', 'blur_intensity'
]


# SECTION: FEATURE ENGINEERING FORMULAS
# Description: Calculates compound metadata metrics from the raw image properties to highlight degradation, cracks, etc.

def _add_engineered_features(data: dict) -> None:
    """Add the 6 derived features to a dict that already has the 15 base features."""

    data['degradation_score'] = (data['noise_level'] * 0.3 + data['dark_ratio'] * 100 +
                                 data['white_ratio'] * 100 + data['edge_count'] * 0.002 +
                                 data['contrast'] * 0.2)

    data['visual_quality_score'] = (data['sharpness'] * 0.4 + data['brightness'] * 0.2 +
                                    data['saturation'] * 0.2 + data['entropy'] * 5)

    data['texture_complexity'] = data['entropy'] * 10 + data['contour_count'] * 0.5

    data['color_richness'] = (data['mean_red'] + data['mean_green'] + data['mean_blue']) / 3

    data['crack_intensity'] = data['white_ratio'] * 100 + data['edge_count'] * 0.001

    data['blur_intensity'] = 1000 / (data['blur_score'] + 1)


# SECTION: COMPUTER VISION FEATURE EXTRACTION
# Description: Converts image bytes into numerical stats via image decoding and filtering algorithms.

def extract_features_from_image(image_bytes):
    """Extracts the 15 base features from raw image bytes."""

    nparr = np.frombuffer(image_bytes, np.uint8)

    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()

    brightness = float(np.mean(gray))

    contrast = float(gray.std())

    edges = cv2.Canny(gray, 100, 200)

    edge_count = int(np.count_nonzero(edges))

    noise_level = float(cv2.meanStdDev(gray)[1][0][0])

    entropy = float(measure.shannon_entropy(gray))

    saturation = float(np.mean(cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 1]))

    dark_ratio = float(np.count_nonzero(gray < 30) / gray.size)

    white_ratio = float(np.count_nonzero(gray > 225) / gray.size)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    height, width = img.shape[:2]

    mean_blue, mean_green, mean_red = cv2.mean(img)[:3]

    return [
        blur_score, brightness, contrast, edge_count, noise_level,
        entropy, saturation, blur_score,  # sharpness == blur_score
        dark_ratio, white_ratio, len(contours), width / height,
        mean_red, mean_green, mean_blue
    ]


# SECTION: PREDICTION ENGINE
# Description: Converts image bytes to processed inputs, transforms using scaler, and queries model.

def get_prediction(image_bytes):
    """Extracts + engineers features from image bytes and returns a restoration label."""

    base_features = extract_features_from_image(image_bytes)
    if base_features is None or __model is None or __scaler is None:
        return None

    try:
        data = dict(zip(__columns, base_features))

        _add_engineered_features(data)

        x = np.array([data[f] for f in FEATURE_ORDER]).reshape(1, -1)

        x_scaled = __scaler.transform(x)

        prediction = __model.predict(x_scaled)[0]

        return {0: "Easy", 1: "Moderate", 2: "Difficult", 3: "Impossible"}.get(prediction, str(prediction))

    except Exception as e:
        print(f"Error during prediction: {e}")
        return None


# SECTION: STATE INITIALIZATION AND ARTIFACT LOADING
# Description: Loads serialized columns list, pickled RandomForest model, and fits standard scaler parameters.

def load_saved_artifacts():
    print("Loading saved artifacts...")
    global __model, __columns, __scaler

    artifacts_dir = os.path.join(os.path.dirname(__file__), "artifacts")

    with open(os.path.join(artifacts_dir, "column.json")) as f:
        __columns = json.load(f)['columns']

    __model = joblib.load(os.path.join(artifacts_dir, "art_restoration_model.pkl"))

    dataset_path = "/model/art_restoration_dataset_new.csv"
    if not os.path.exists(dataset_path):
        dataset_path = os.path.join(os.path.dirname(__file__), "..", "model", "art_restoration_dataset_new.csv")

    df = pd.read_csv(dataset_path)

    # Applies duplicate feature transformations directly on training DataFrame to match training distribution features.
    # If these formulas deviate from _add_engineered_features, predictions will skew.
    df['degradation_score'] = (df['noise_level'] * 0.3 + df['dark_ratio'] * 100 +
                               df['white_ratio'] * 100 + df['edge_count'] * 0.002 +
                               df['contrast'] * 0.2)
    df['visual_quality_score'] = (df['sharpness'] * 0.4 + df['brightness'] * 0.2 +
                                  df['saturation'] * 0.2 + df['entropy'] * 5)
    df['texture_complexity'] = df['entropy'] * 10 + df['contour_count'] * 0.5
    df['color_richness'] = (df['mean_red'] + df['mean_green'] + df['mean_blue']) / 3
    df['crack_intensity'] = df['white_ratio'] * 100 + df['edge_count'] * 0.001
    df['blur_intensity'] = 1000 / (df['blur_score'] + 1)

    __scaler = StandardScaler()
    __scaler.fit(df[FEATURE_ORDER])
    print("Artifacts loaded and scaler fitted.")


# SECTION: HELPER METADATA ENDPOINTS
# Description: Fetch functions used to fetch configuration properties.

def get_column_names():
    return __columns


# SECTION: TEST TRIGGER
# Description: Automatically loads assets when running util.py directly.
if __name__ == "__main__":
    load_saved_artifacts()
