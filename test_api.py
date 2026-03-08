import requests
try:
    resp = requests.get('http://127.0.0.1:5000/api/problems', timeout=5)
    print("Status:", resp.status_code)
    print("Response:")
    print(resp.json())
except Exception as e:
    print("Error:", e)
