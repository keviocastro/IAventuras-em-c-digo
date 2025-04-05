from fastapi.testclient import TestClient
from http import HTTPStatus
from challenge.app import app


def test_read_root_deve_retornar_ok_e_hello_world():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"message": "Hello World!"}
