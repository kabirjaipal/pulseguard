import pytest
from unittest.mock import patch, MagicMock
from app.models.monitoring_result import MonitoringResult

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

def test_endpoints_crud_and_history(client, db):
    headers = get_auth_headers(client)

    # 1. Create Project
    proj_res = client.post(
        "/api/projects/",
        json={"name": "Workspace", "description": "Desc"},
        headers=headers
    )
    project_id = proj_res.json()["id"]

    # 2. Create Endpoint
    end_res = client.post(
        "/api/endpoints/",
        json={
            "name": "Target",
            "url": "https://httpbin.org/status/200",
            "method": "GET",
            "check_interval": 30,
            "is_active": True,
            "project_id": project_id
        },
        headers=headers
    )
    endpoint_id = end_res.json()["id"]

    # 3. Get endpoint by ID
    get_res = client.get(f"/api/endpoints/{endpoint_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Target"

    # 4. Get endpoints by project
    get_proj_res = client.get(f"/api/endpoints/project/{project_id}", headers=headers)
    assert get_proj_res.status_code == 200
    assert len(get_proj_res.json()) == 1

    # 5. Get endpoints by unauthorized project
    headers2 = get_auth_headers(client, "unauth@pulseguard.io")
    get_proj_res2 = client.get(f"/api/endpoints/project/{project_id}", headers=headers2)
    assert get_proj_res2.status_code == 404

    # 6. Get history (empty list at first)
    hist_res = client.get(f"/api/endpoints/{endpoint_id}/history", headers=headers)
    assert hist_res.status_code == 200
    assert len(hist_res.json()) == 0

    # 7. Add history records manually to DB
    for _ in range(5):
        mr = MonitoringResult(
            endpoint_id=endpoint_id,
            status_code=200,
            response_time_ms=150,
            is_healthy=True
        )
        db.add(mr)
    db.commit()

    hist_res2 = client.get(f"/api/endpoints/{endpoint_id}/history?limit=3", headers=headers)
    assert hist_res2.status_code == 200
    assert len(hist_res2.json()) == 3

    # 8. Delete Endpoint
    del_res = client.delete(f"/api/endpoints/{endpoint_id}", headers=headers)
    assert del_res.status_code == 204

    # 9. Get deleted endpoint returns 404
    get_res_deleted = client.get(f"/api/endpoints/{endpoint_id}", headers=headers)
    assert get_res_deleted.status_code == 404

def test_get_latest_endpoint_result_caching(client, db):
    headers = get_auth_headers(client)

    # Create project and endpoint
    proj_res = client.post(
        "/api/projects/",
        json={"name": "Workspace", "description": "Desc"},
        headers=headers
    )
    project_id = proj_res.json()["id"]

    end_res = client.post(
        "/api/endpoints/",
        json={
            "name": "Target",
            "url": "https://httpbin.org/status/200",
            "method": "GET",
            "check_interval": 30,
            "is_active": True,
            "project_id": project_id
        },
        headers=headers
    )
    endpoint_id = end_res.json()["id"]

    # Requesting latest results when none exist should return 404
    latest_res_none = client.get(f"/api/endpoints/{endpoint_id}/latest", headers=headers)
    assert latest_res_none.status_code == 404

    # Add a result manually
    mr = MonitoringResult(
        endpoint_id=endpoint_id,
        status_code=200,
        response_time_ms=100,
        is_healthy=True
    )
    db.add(mr)
    db.commit()

    # Test cache miss (Redis empty, fall back to DB)
    with patch("app.routers.endpoints.redis_client") as mock_redis:
        mock_redis.get.return_value = None
        latest_res = client.get(f"/api/endpoints/{endpoint_id}/latest", headers=headers)
        assert latest_res.status_code == 200
        assert latest_res.json()["status_code"] == 200
        # Check that it tried to write to Redis
        mock_redis.setex.assert_called_once()

    # Test cache hit (Redis returns JSON)
    import json
    import datetime
    cached_payload = {
        "id": 1,
        "endpoint_id": endpoint_id,
        "status_code": 200,
        "response_time_ms": 100,
        "is_healthy": True,
        "error_message": None,
        "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    with patch("app.routers.endpoints.redis_client") as mock_redis:
        mock_redis.get.return_value = json.dumps(cached_payload)
        latest_res = client.get(f"/api/endpoints/{endpoint_id}/latest", headers=headers)
        assert latest_res.status_code == 200
        assert latest_res.json()["status_code"] == 200
        # Database query shouldn't have been needed, and redis setex not called
        mock_redis.setex.assert_not_called()

def test_trigger_ping_manually(client):
    headers = get_auth_headers(client)

    proj_res = client.post(
        "/api/projects/",
        json={"name": "Workspace", "description": "Desc"},
        headers=headers
    )
    project_id = proj_res.json()["id"]

    end_res = client.post(
        "/api/endpoints/",
        json={
            "name": "Target",
            "url": "https://httpbin.org/status/200",
            "method": "GET",
            "check_interval": 30,
            "is_active": True,
            "project_id": project_id
        },
        headers=headers
    )
    endpoint_id = end_res.json()["id"]

    with patch("app.core.tasks.ping_endpoint_task.delay") as mock_delay:
        ping_res = client.post(f"/api/endpoints/{endpoint_id}/ping", headers=headers)
        assert ping_res.status_code == 202
        assert ping_res.json()["message"] == "Check triggered and queued."
        mock_delay.assert_called_once_with(endpoint_id)
