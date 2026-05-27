import pytest

# Helper to register and log in a user, returning the auth headers
def get_auth_headers(client, email="user@pulseguard.io", password="password123"):
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

def test_create_project_and_endpoint(client):
    headers = get_auth_headers(client)

    # 1. Create a project
    proj_res = client.post(
        "/api/projects/",
        json={"name": "Test Platform", "description": "Monitoring test server"},
        headers=headers
    )
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    # 2. Create an endpoint under that project
    end_res = client.post(
        "/api/endpoints/",
        json={
            "name": "Health Ping",
            "url": "https://httpbin.org/status/200",
            "method": "GET",
            "check_interval": 30,
            "is_active": True,
            "project_id": project_id
        },
        headers=headers
    )
    assert end_res.status_code == 201
    endpoint_data = end_res.json()
    assert endpoint_data["name"] == "Health Ping"
    assert endpoint_data["project_id"] == project_id

def test_create_endpoint_unauthorized_project(client):
    # Register two separate users
    user1_headers = get_auth_headers(client, "user1@pulseguard.io")
    user2_headers = get_auth_headers(client, "user2@pulseguard.io")

    # User 1 creates a project
    proj_res = client.post(
        "/api/projects/",
        json={"name": "User 1 Project", "description": "Private project"},
        headers=user1_headers
    )
    project_id = proj_res.json()["id"]

    # User 2 attempts to create an endpoint in User 1's project
    end_res = client.post(
        "/api/endpoints/",
        json={
            "name": "Intruder Ping",
            "url": "https://httpbin.org/status/200",
            "method": "GET",
            "check_interval": 30,
            "is_active": True,
            "project_id": project_id
        },
        headers=user2_headers
    )
    assert end_res.status_code == 404
    assert "Project not found or not owned by you" in end_res.json()["detail"]

def test_get_endpoints(client):
    headers = get_auth_headers(client)

    # Create project and endpoint
    proj_res = client.post(
        "/api/projects/",
        json={"name": "My Workspace", "description": "Testing endpoints retrieval"},
        headers=headers
    )
    project_id = proj_res.json()["id"]

    client.post(
        "/api/endpoints/",
        json={
            "name": "Endpoint 1",
            "url": "https://httpbin.org/delay/1",
            "method": "GET",
            "check_interval": 60,
            "is_active": True,
            "project_id": project_id
        },
        headers=headers
    )

    # Get endpoints list
    list_res = client.get("/api/endpoints/", headers=headers)
    assert list_res.status_code == 200
    endpoints = list_res.json()
    assert len(endpoints) == 1
    assert endpoints[0]["name"] == "Endpoint 1"
