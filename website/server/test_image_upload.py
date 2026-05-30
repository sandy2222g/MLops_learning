import requests
import os

def test_image_upload():
    base_url = "http://localhost:5000"
    
    print("--- Starting Image Upload Test ---")
    
    # 1. Verify artifacts folder
    if not os.path.exists("server/artifacts"):
        print("❌ Error: server/artifacts folder is missing!")
        return

    # 2. Test Image Upload
    # We'll try to find any image in the current directory or provide a mock
    image_path = "test_image.jpg" # Update this to a real image path if you have one
    
    # Create a dummy image for testing if it doesn't exist
    if not os.path.exists(image_path):
        import numpy as np
        import cv2
        dummy_img = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
        cv2.imwrite(image_path, dummy_img)
        print(f"Created dummy image: {image_path}")

    print(f"\nTesting /predict_restoration with file: {image_path}...")
    
    try:
        with open(image_path, 'rb') as img:
            files = {'file': (image_path, img, 'image/jpeg')}
            response = requests.post(f"{base_url}/predict_restoration", files=files)
            
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Prediction: {result.get('prediction')}")
        else:
            print(f"❌ Failed! Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error during upload test: {e}")
    finally:
        # Cleanup dummy image
        if os.path.exists(image_path):
            os.remove(image_path)

    print("\n--- Test Completed ---")

if __name__ == "__main__":
    test_image_upload()
