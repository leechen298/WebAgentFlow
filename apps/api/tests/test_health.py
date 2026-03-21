from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "code": 0,
        "data": {"status": "ok", "database": "ok"},
        "msg": "ok",
    }


def test_docs_available(client: TestClient) -> None:
    response = client.get("/docs")

    assert response.status_code == 200
