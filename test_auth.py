import requests

# Test login and auth
API_URL = "http://localhost:8000/api"

print("Testing login...")
login_response = requests.post(
    f"{API_URL}/auth/login",
    data={"username": "teste3@teste.com", "password": "123456"}
)
print(f"Login status: {login_response.status_code}")

if login_response.status_code == 200:
    token = login_response.json()["access_token"]
    print(f"Token obtained: {token[:50]}...")
    
    print("\nTesting /auth/me...")
    me_response = requests.get(
        f"{API_URL}/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Me status: {me_response.status_code}")
    print(f"Me response: {me_response.text}")
else:
    print(f"Login failed: {login_response.text}")
