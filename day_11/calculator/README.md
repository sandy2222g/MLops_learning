# Quantum Calc - Dockerized Flask Calculator App

A beautiful, high-fidelity calculator web application built with a **Python Flask** backend and a glassmorphic **HTML/CSS/JS** frontend. Designed for MLOps demonstration, it showcases how a containerized web application communicates with API endpoints in real-time.

## Features
- ⚡ **Dual Calculation Modes**: Toggle between **Flask API** (calculations processed via Flask POST endpoints) and **Local JS** (offline client-side calculations).
- 📡 **Telemetry Network Console**: Visualizes raw JSON payloads sent to and received from the server in real-time, showing response times.
- 🕰️ **History Tape**: Logs the history of operations with separate indicator badges for Flask server calculations and local offline calculations.
- 🎨 **Premium Glassmorphism Design**: High-end midnight styling, smooth animations, and key interactive state changes.

---

## 🚀 Running Natively

1. Navigate to the calculator directory:
   ```bash
   cd calculator
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the Flask server:
   ```bash
   python app.py
   ```
4. Open your browser and navigate to `http://localhost:5000`.

---

## 🐳 Running with Docker

You can containerize and run the application using Docker in two steps:

### 1. Build the Docker Image
Inside the `calculator` folder, run:
```bash
docker build -t quantum-calculator .
```

### 2. Run the Container
Start the container and map the internal port `5000` to your local port `5000`:
```bash
docker run -p 5000:5000 quantum-calculator
```

Once running, access the web calculator at `http://localhost:5000`.
- In **Flask API Mode**, you will see the calculations hit the Flask endpoint hosted inside your Docker container with live JSON request logging in the network panel!
