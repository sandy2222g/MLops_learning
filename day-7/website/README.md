# MLOps Lab: Art Restoration Complexity Predictor

This project is a comprehensive MLOps dashboard designed to analyze artwork images and predict their restoration complexity using machine learning and computer vision.

## Project Overview

The system extracts visual features from an uploaded artwork image, calculates additional engineered features, and uses a trained Random Forest model to categorize the restoration difficulty into four levels: **Easy**, **Moderate**, **Difficult**, or **Impossible**.

### Key Features
- **Real-time Image Analysis**: Upload photos directly to the dashboard.
- **Automated Feature Extraction**: Uses OpenCV and Scikit-Image to calculate 15 different visual metrics (Blur, Noise, Entropy, Color profiles, etc.).
- **ML Inference**: Powered by a Scikit-Learn Random Forest model.
- **Modern UI**: Built with React 19, Tailwind CSS, and Framer Motion.
- **Responsive Design**: Fully functional on desktop and mobile devices.
- **Theme Support**: Includes both Light and Dark modes.

---

## Project Structure

```text
/
├── client/                # React Frontend (Vite)
│   ├── src/
│   │   ├── components/    # UI Components (Header, Dashboard, UploadSection)
│   │   └── App.tsx        # Main application entry
│   └── package.json
├── server/                # Python Flask Backend
│   ├── artifacts/         # ML Model and column references
│   │   ├── art_restoration_model.pkl
│   │   └── column.json
│   ├── server.py          # API Routing and request handling
│   ├── util.py            # Image processing and prediction logic
│   └── requirements.txt   # Python dependencies
└── model/                 # Data and Training context
    ├── art_restoration_dataset_new.csv
    └── final artwork.ipynb
```

---

## Setup and Installation

### 1. Backend Setup
Ensure you have Python 3.10+ installed.

```powershell
# Navigate to server directory
cd server

# Install dependencies
pip install -r requirements.txt

# Start the Flask server
python server.py
```
The backend will run at `http://localhost:5000`.

### 2. Frontend Setup
Ensure you have Node.js installed.

```powershell
# Navigate to client directory
cd client

# Install dependencies
npm install

# Start the Vite development server
npm run dev
```
The frontend will be available at `http://localhost:3000`.

---

## How it Works

1. **Upload**: The user uploads an image via the React frontend.
2. **Transfer**: The image is sent as a multipart/form-data request to the Flask backend.
3. **Extraction**: `util.py` uses OpenCV to decode the image and calculate 15 base features.
4. **Engineering**: 6 additional features are calculated (e.g., `degradation_score`, `visual_quality_score`) to match the training data.
5. **Scaling**: A `StandardScaler` is fitted to the base dataset to ensure input consistency.
6. **Prediction**: The 21-feature vector is passed to the Random Forest model.
7. **Display**: The UI receives the prediction and the raw metrics to update the dashboard.

## Disclaimer
This system uses a **text-based machine learning model** trained on numerical image features. Results are based on statistical extraction from pixel data and may not be fully accurate for all artwork styles or edge cases.
