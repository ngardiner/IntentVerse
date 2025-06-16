import pytest
from fastapi.testclient import TestClient
from app.security import get_password_hash, verify_password, create_access_token, decode_access_token

# --- Unit Tests for Security Functions ---

def test_password_hashing():
    """Tests that password hashing and verification work correctly."""
    password = "testpassword"
    hashed_password = get_password_hash(password)
    assert hashed_password != password
    assert verify_password(password, hashed_password)
    assert not verify_password("wrongpassword", hashed_password)

def test_jwt_token_handling():
    """Tests the creation and decoding of JWT tokens."""
    username = "testuser"
    token = create_access_token(data={"sub": username})
    assert isinstance(token, str)
    
    decoded_username = decode_access_token(token)
    assert decoded_username == username

def test_decode_invalid_token():
    """Tests that decoding an invalid token returns None."""
    assert decode_access_token("invalid.token.string") is None


# --- Integration Tests for API Endpoints ---

def test_create_user(client: TestClient):
    """Tests user creation via the API."""
    response = client.post("/users/", json={"username": "testuser", "password": "testpassword"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert "id" in data

def test_create_duplicate_user(client: TestClient):
    """Tests that creating a user with an existing username fails."""
    # Create the first user
    client.post("/users/", json={"username": "duplicate", "password": "password123"})
    # Attempt to create the second user with the same username
    response = client.post("/users/", json={"username": "duplicate", "password": "password456"})
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]

def test_login_for_access_token(client: TestClient):
    """Tests the /auth/login endpoint with valid credentials."""
    # Create a user first
    client.post("/users/", json={"username": "loginuser", "password": "password"})
    
    # Attempt to log in
    login_data = {"username": "loginuser", "password": "password"}
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_with_invalid_credentials(client: TestClient):
    """Tests the /auth/login endpoint with an incorrect password."""
    client.post("/users/", json={"username": "loginuser2", "password": "password"})
    
    login_data = {"username": "loginuser2", "password": "wrongpassword"}
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]

def test_read_current_user(client: TestClient):
    """Tests the protected /users/me endpoint."""
    # Create user and log in to get a token
    client.post("/users/", json={"username": "me_user", "password": "password"})
    login_response = client.post("/auth/login", data={"username": "me_user", "password": "password"})
    token = login_response.json()["access_token"]
    
    # Access the protected endpoint with the token
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "me_user"

def test_read_current_user_no_token(client: TestClient):
    """Tests that accessing a protected endpoint without a token fails."""
    response = client.get("/users/me")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]