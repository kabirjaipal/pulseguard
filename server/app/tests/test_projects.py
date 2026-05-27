import pytest

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

def test_project_crud(client):
    headers1 = get_auth_headers(client, "u1@pulseguard.io")
    headers2 = get_auth_headers(client, "u2@pulseguard.io")

    # 1. Create project for user 1
    create_res = client.post(
        "/api/projects/",
        json={"name": "Project 1", "description": "My first project"},
        headers=headers1
    )
    assert create_res.status_code == 201
    proj_data = create_res.json()
    assert proj_data["name"] == "Project 1"
    assert proj_data["description"] == "My first project"
    proj_id = proj_data["id"]

    # 2. Get list of projects for user 1
    list_res = client.get("/api/projects/", headers=headers1)
    assert list_res.status_code == 200
    projects = list_res.json()
    assert len(projects) == 1
    assert projects[0]["id"] == proj_id

    # 3. Get list of projects for user 2 (should be empty)
    list_res2 = client.get("/api/projects/", headers=headers2)
    assert list_res2.status_code == 200
    assert len(list_res2.json()) == 0

    # 4. Get specific project details for user 1
    get_res = client.get(f"/api/projects/{proj_id}", headers=headers1)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Project 1"

    # 5. Try getting specific project belonging to user 1 using user 2 credentials
    get_res2 = client.get(f"/api/projects/{proj_id}", headers=headers2)
    assert get_res2.status_code == 404
    assert get_res2.json()["detail"] == "Project not found or not owned by you."

    # 6. Try getting non-existent project
    get_res3 = client.get("/api/projects/99999", headers=headers1)
    assert get_res3.status_code == 404

    # 7. Try deleting user 1's project using user 2 credentials
    del_res = client.delete(f"/api/projects/{proj_id}", headers=headers2)
    assert del_res.status_code == 404

    # 8. Delete user 1's project using user 1 credentials
    del_res2 = client.delete(f"/api/projects/{proj_id}", headers=headers1)
    assert del_res2.status_code == 204

    # 9. Get specific project should now return 404
    get_res4 = client.get(f"/api/projects/{proj_id}", headers=headers1)
    assert get_res4.status_code == 404
