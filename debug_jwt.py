"""Debug JWT token issues - Test after fix"""
import requests

API_URL = "http://localhost:8000/api"

# Test login - this will get a NEW token with sub as string
print("1. Testing login (getting new token)...")
login_response = requests.post(
    f"{API_URL}/auth/login",
    data={"username": "teste3@teste.com", "password": "123456"}
)
print(f"   Status: {login_response.status_code}")

if login_response.status_code == 200:
    token = login_response.json()["access_token"]
    print(f"   Token: {token[:80]}...")
    
    # Test /auth/me directly
    print("\n2. Testing /auth/me...")
    me_response = requests.get(
        f"{API_URL}/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"   Status: {me_response.status_code}")
    print(f"   Response: {me_response.text}")
    
    if me_response.status_code == 200:
        print("\n✅ SUCCESS! JWT authentication is working!")
        
        # Test creating a transaction
        print("\n3. Testing create transaction...")
        from datetime import date
        tx_data = {
            "valor_total": 150.00,
            "descricao": "Teste de transação",
            "categoria": "Teste",
            "tipo": "saida_debito",
            "data_compra": str(date.today()),
            "num_parcelas": 1
        }
        tx_response = requests.post(
            f"{API_URL}/transactions/",
            json=tx_data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        print(f"   Status: {tx_response.status_code}")
        print(f"   Response: {tx_response.text[:200]}...")
    else:
        print("\n❌ FAILED! Check backend logs for details.")
else:
    print(f"   Login failed: {login_response.text}")
