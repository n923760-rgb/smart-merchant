from uuid import uuid4


def test_authentication_rotation_revocation_and_disabled_membership(client, merchant):
    denied = client.post(
        "/api/v1/auth/login", json={"email": merchant["email"], "password": "wrong"}
    )
    assert denied.status_code == 401
    assert denied.json()["code"] == "AUTHENTICATION_FAILED"
    assert denied.json()["request_id"] == denied.headers["X-Request-ID"]
    assert client.get("/api/v1/auth/me", headers=merchant["headers"]).status_code == 200
    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": merchant["refresh"]})
    assert rotated.status_code == 200
    assert (
        client.post("/api/v1/auth/refresh", json={"refresh_token": merchant["refresh"]}).status_code
        == 401
    )
    new_token = rotated.json()["refresh_token"]
    assert (
        client.post(
            "/api/v1/auth/logout", json={"refresh_token": new_token}, headers=merchant["headers"]
        ).status_code
        == 204
    )
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": new_token}).status_code == 401


def test_tenant_isolation_roles_audit_and_last_owner(client, merchant):
    other_email = f"other-{uuid4()}@example.test"
    other = client.post(
        "/api/v1/bootstrap",
        headers={"X-Bootstrap-Key": "test-bootstrap-key-for-disposable-test-db-000000"},
        json={
            "owner_name": "Other",
            "owner_email": other_email,
            "owner_password": "secure-test-password-123",
            "organization_name": "Other Merchant",
        },
    )
    assert other.status_code == 201
    other_org = other.json()["organization"]["id"]
    foreign_context = {**merchant["headers"], "X-Organization-ID": other_org}
    assert client.get("/api/v1/organizations", headers=foreign_context).status_code == 404
    branch = client.post(
        "/api/v1/branches", headers=merchant["headers"], json={"name": "Abha", "code": "ABH01"}
    )
    assert branch.status_code == 201, branch.text
    branch_id = branch.json()["id"]
    other_login = client.post(
        "/api/v1/auth/login", json={"email": other_email, "password": "secure-test-password-123"}
    ).json()
    other_headers = {
        "Authorization": f"Bearer {other_login['access_token']}",
        "X-Organization-ID": other_org,
    }
    assert client.get(f"/api/v1/branches/{branch_id}", headers=other_headers).status_code == 404
    assert (
        client.post(
            "/api/v1/terminals",
            headers=other_headers,
            json={"name": "Foreign", "device_identifier": str(uuid4()), "branch_id": branch_id},
        ).status_code
        == 404
    )
    user_id = client.get("/api/v1/auth/me", headers=merchant["headers"]).json()["id"]
    assert (
        client.post(f"/api/v1/users/{user_id}/disable", headers=merchant["headers"]).status_code
        == 409
    )
    terminal = client.post(
        "/api/v1/terminals",
        headers=merchant["headers"],
        json={"name": "Front desk", "device_identifier": str(uuid4()), "branch_id": branch_id},
    )
    assert terminal.status_code == 201
    assert (
        client.post(
            f"/api/v1/terminals/{terminal.json()['id']}/revoke", headers=merchant["headers"]
        ).status_code
        == 200
    )
    actions = [
        a["action"]
        for a in client.get("/api/v1/audit", headers=merchant["headers"]).json()["items"]
    ]
    assert "BRANCH_CREATED" in actions and "TERMINAL_REVOKED" in actions
    assert client.delete("/api/v1/audit", headers=merchant["headers"]).status_code == 405


def test_branch_scoping_and_escalation(client, merchant):
    first = client.post(
        "/api/v1/branches", headers=merchant["headers"], json={"name": "Abha", "code": "ABH02"}
    ).json()["id"]
    second = client.post(
        "/api/v1/branches", headers=merchant["headers"], json={"name": "Khamis", "code": "KHM01"}
    ).json()["id"]
    email = f"manager-{uuid4()}@example.test"
    user = client.post(
        "/api/v1/users",
        headers=merchant["headers"],
        json={"name": "Manager", "email": email, "password": "secure-test-password-123"},
    ).json()
    manager_role = next(
        r
        for r in client.get("/api/v1/roles", headers=merchant["headers"]).json()["items"]
        if r["code"] == "MANAGER"
    )
    assert (
        client.post(
            f"/api/v1/users/{user['id']}/roles",
            headers=merchant["headers"],
            json={"role_id": manager_role["id"], "branch_id": first},
        ).status_code
        == 201
    )
    detail = client.get(f"/api/v1/users/{user['id']}", headers=merchant["headers"])
    assert detail.status_code == 200
    assert detail.json()["roles"][0]["branch_id"] == first
    token = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "secure-test-password-123"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": merchant["org"]}
    assert client.get(f"/api/v1/branches/{first}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/branches/{second}", headers=headers).status_code == 403
    assert (
        client.post(
            "/api/v1/branches", headers=headers, json={"name": "Forbidden", "code": "FOR01"}
        ).status_code
        == 403
    )
    assert client.get("/api/v1/roles", headers=headers).status_code == 403
    actions = [
        a["action"]
        for a in client.get("/api/v1/audit", headers=merchant["headers"]).json()["items"]
    ]
    assert "ROLE_ASSIGNED" in actions
