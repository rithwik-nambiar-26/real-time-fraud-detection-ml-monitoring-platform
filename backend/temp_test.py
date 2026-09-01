from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
print('health status', client.get('/health').status_code)
print(client.get('/health').json())
