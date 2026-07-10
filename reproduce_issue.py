import requests
import io
from PIL import Image

def test_image_resize():
    url = "http://127.0.0.1:5000/api/image/resize"
    
    # Create a dummy image
    img = Image.new('RGB', (100, 100), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)
    
    files = {'images': ('test.jpg', img_byte_arr, 'image/jpeg')}
    data = {'width': 50, 'height': 50, 'format': 'webp'}
    
    try:
        response = requests.post(url, files=files, data=data)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Success!")
            print(f"Content-Type: {response.headers.get('Content-Type')}")
            print(f"Content-Disposition: {response.headers.get('Content-Disposition')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_image_resize()
