import pytest
from app.models.monitoring_result import MonitoringResult
from app.models.project import Project
from app.models.endpoint import Endpoint

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

def test_incidents_flow(client, db):
    headers = get_auth_headers(client)

    # 1. Create a project
    proj_res = client.post(
        "/api/projects/",
        json={"name": "Alert System Workspace", "description": "Analyzing failures"},
        headers=headers
    )
    project_id = proj_res.json()["id"]

    # 2. Create an endpoint
    end_res = client.post(
        "/api/endpoints/",
        json={
            "name": "Failed API",
            "url": "https://httpbin.org/status/500",
            "method": "GET",
            "check_interval": 30,
            "is_active": True,
            "project_id": project_id
        },
        headers=headers
    )
    endpoint_id = end_res.json()["id"]

    # 3. Requesting analysis when there are no failed logs should return 400 Bad Request
    analyze_res = client.post(
        f"/api/incidents/endpoint/{endpoint_id}/analyze",
        headers=headers
    )
    assert analyze_res.status_code == 400
    assert "No failed check logs found" in analyze_res.json()["detail"]

    # 4. Insert failed checks to database manually
    db_endpoint = db.query(Endpoint).filter(Endpoint.id == endpoint_id).first()
    for i in range(3):
        res_log = MonitoringResult(
            endpoint_id=endpoint_id,
            status_code=500,
            response_time_ms=120,
            is_healthy=False,
            error_message="Non-2xx status code returned: 500"
        )
        db.add(res_log)
    db.commit()

    # 5. Successfully trigger manual AI analysis
    analyze_res = client.post(
        f"/api/incidents/endpoint/{endpoint_id}/analyze",
        headers=headers
    )
    assert analyze_res.status_code == 201
    analysis_data = analyze_res.json()
    assert "summary" in analysis_data
    assert "suggestions" in analysis_data
    assert analysis_data["endpoint_id"] == endpoint_id

    # 6. Retrieve all analyses for endpoint
    get_analyses_res = client.get(
        f"/api/incidents/endpoint/{endpoint_id}",
        headers=headers
    )
    assert get_analyses_res.status_code == 200
    analyses = get_analyses_res.json()
    assert len(analyses) == 1
    assert analyses[0]["id"] == analysis_data["id"]

    # 7. Try getting incident analysis for non-existent endpoint or unauthorized user
    headers2 = get_auth_headers(client, "otheruser@pulseguard.io")
    get_unauth_res = client.get(
        f"/api/incidents/endpoint/{endpoint_id}",
        headers=headers2
    )
    assert get_unauth_res.status_code == 404
