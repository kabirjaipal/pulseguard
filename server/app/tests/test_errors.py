import pytest
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError

def get_auth_headers(client, email="erroruser@pulseguard.io", password="password123"):
    client.post(
        "/api/auth/signup",
        json={"email": email, "password": password}
    )
    login_res = client.post(
        "/api/auth/login",
        data={"username": email, "password": password}
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_sqlalchemy_error_handler(client):
    headers = get_auth_headers(client)
    
    from fastapi.testclient import TestClient
    from app.main import app
    no_raise_client = TestClient(app, raise_server_exceptions=False)
    
    # Mock the database query inside get_projects route to raise SQLAlchemyError
    with patch("sqlalchemy.orm.Session.query") as mock_query:
        mock_query.side_effect = SQLAlchemyError("Simulated database failure")
        response = no_raise_client.get("/api/projects/", headers=headers)
        
        assert response.status_code == 500
        assert response.json() == {"detail": "A database error occurred."}

def test_generic_exception_handler(client):
    headers = get_auth_headers(client)
    
    from fastapi.testclient import TestClient
    from app.main import app
    no_raise_client = TestClient(app, raise_server_exceptions=False)
    
    # Mock database query to raise a generic Exception
    with patch("sqlalchemy.orm.Session.query") as mock_query:
        mock_query.side_effect = Exception("Simulated unhandled exception")
        response = no_raise_client.get("/api/projects/", headers=headers)
        
        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error."}

