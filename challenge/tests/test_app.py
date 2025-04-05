from fastapi.testclient import TestClient
from http import HTTPStatus
from challenge.app import app
from challenge.models.entities import Aluno, Plano, CheckIn


def test_read_root_deve_retornar_ok_e_hello_world():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"message": "Hello World!"}


def test_listar_alunos():
    client = TestClient(app)
    response = client.get("/alunos")
    print(response.json())
    assert response.status_code == HTTPStatus.OK


def test_adicionar_aluno():
    client = TestClient(app)
    response = client.post(
        "/alunos",
        json={
            "nome": "João Silva",
            "email": "joao@email.com",
            "telefone": "123456789",
            "plano_id": 1,
            "data_nascimento": "1990-01-01",
            "sexo": "M",
            "endereco": "Rua A, 123",
            "status": "ativo",
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["nome"] == "João Silva"
