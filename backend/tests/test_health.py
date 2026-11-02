from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_says_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_schema_lists_health():
    # The frontend's typed client is generated from this schema (D-001).
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/health" in response.json()["paths"]


def test_unknown_path_gives_a_plain_json_error():
    response = client.get("/nope")

    assert response.status_code == 404
    assert "detail" in response.json()


def test_wrong_method_is_refused():
    response = client.post("/health")

    assert response.status_code == 405


def test_allowed_origin_gets_cors_header():
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_other_origin_gets_no_cors_header():
    response = client.get("/health", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers
