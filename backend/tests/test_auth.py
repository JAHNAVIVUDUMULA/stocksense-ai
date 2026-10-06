import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.models.user import User

client = TestClient(app)

def test_register_and_login():
    email = "test_vendor_unique@stocksense.ai"
    # Cleanup if exists
    db = SessionLocal()
    db.query(User).filter(User.email == email).delete()
    db.commit()
    db.close()

    # 1. Register
    reg_res = client.post("/api/auth/register", json={
        "name": "Test Vendor",
        "email": email,
        "password": "strongpassword123"
    })
    assert reg_res.status_code == 201
    data = reg_res.json()
    assert "access_token" in data
    assert data["user"]["email"] == email

    # 2. Duplicate registration should fail
    dup_res = client.post("/api/auth/register", json={
        "name": "Test Vendor",
        "email": email,
        "password": "strongpassword123"
    })
    assert dup_res.status_code == 400

    # 3. Login with correct password
    login_res = client.post("/api/auth/login", json={
        "email": email,
        "password": "strongpassword123"
    })
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # 4. Login with invalid password
    bad_res = client.post("/api/auth/login", json={
        "email": email,
        "password": "wrongpassword"
    })
    assert bad_res.status_code == 401

    # 5. Access /api/auth/me with bearer token
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email
