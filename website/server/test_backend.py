import requests
import json
import numpy as np

def test_backend():
    base_url = "http://localhost:5000"
    
    print("--- Starting Backend Tests ---")
    
    # 1. Test Health/Columns Endpoint
    print("\n1. Testing /get_column_names...")
    try:
        response = requests.get(f"{base_url}/get_column_names")
        if response.status_code == 200:
            columns = response.json().get('columns')
            print(f"✅ Success! Found {len(columns)} columns.")
            print(f"Columns: {columns[:5]}... (total {len(columns)})")
        else:
            print(f"❌ Failed! Status Code: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        print("Make sure the server is running (python server/server.py)")
        return

    # 2. Test Prediction Endpoint
    print("\n2. Testing /predict_restoration...")
    # Create mock features based on the number of columns
    mock_features = [0.5] * len(columns) 
    
    payload = {
        "features": mock_features
    }
    
    try:
        response = requests.post(
            f"{base_url}/predict_restoration",
            json=payload
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Prediction received: {result.get('prediction')}")
            print(f"Full Response: {result}")
        else:
            print(f"❌ Failed! Status Code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error during prediction test: {e}")

    print("\n--- Tests Completed ---")

if __name__ == "__main__":
    test_backend()
