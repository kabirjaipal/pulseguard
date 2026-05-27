def test_signup_successful(client):
    response = client.post(
        "/api/auth/signup",
        json={"email": "testuser@pulseguard.io", "password": "securepassword123"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "testuser@pulseguard.io"
    assert "id" in data

def test_signup_duplicate_email(client):
    # Register first user
    client.post(
        "/api/auth/signup",
        json={"email": "duplicate@pulseguard.io", "password": "password123"}
    )
    # Register same email again
    response = client.post(
        "/api/auth/signup",
        json={"email": "duplicate@pulseguard.io", "password": "password456"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered."

def test_login_successful(client):
    # Register a user
    client.post(
        "/api/auth/signup",
        json={"email": "loginuser@pulseguard.io", "password": "mypassword"}
    )
    # Log in
    response = client.post(
        "/api/auth/login",
        data={"username": "loginuser@pulseguard.io", "password": "mypassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_incorrect_password(client):
    client.post(
        "/api/auth/signup",
        json={"email": "wrongpass@pulseguard.io", "password": "correctpassword"}
    )
    response = client.post(
        "/api/auth/login",
        data={"username": "wrongpass@pulseguard.io", "password": "incorrectpassword"}
    )
    assert response.status_code == 400
    assert "Incorrect email or password." in response.json()["detail"]
