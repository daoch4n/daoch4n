import requests
import sys

def check_server(url):
    try:
        response = requests.get(url)
        print(f"Status code: {response.status_code}")
        print(f"Content: {response.text[:100]}...")
        return response.status_code
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    url = "http://localhost:12393"
    status_code = check_server(url)
    if status_code == 200:
        print("Server is running correctly")
    else:
        print("Server is not running correctly")
        sys.exit(1)
