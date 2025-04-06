import random
from fastapi.testclient import TestClient
from http import HTTPStatus
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app import app
from datetime import datetime, timedelta
import json
from unittest.mock import patch, MagicMock

from rabbitmq.consumers.batch_checkin_consumer import (
    processar_entrada,
    processar_saida,
    obter_data_evento,
    validar_aluno,
    processar_checkin_em_lote,
)


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


# def test_adicionar_aluno():
#     client = TestClient(app)
#     response = client.post(
#         "/aluno/registro",
#         json={
#             "nome": "Hugo",
#             "email": "test@email.com",
#             "telefone": "123456789",
#             "plano_id": 1,
#             "data_nascimento": "1990-01-01",
#             "sexo": "M",
#             "endereco": "Rua A, 123",
#             "status": "ativo",
#         },
#     )
#     assert response.status_code == HTTPStatus.CREATED
#     assert response.json()["nome"] == "Hugo"


def test_checkin_aluno():
    client = TestClient(app)
    response = client.post(
        "/aluno/checkin",
        json={
            "aluno_id": 1,
            "data_entrada": datetime.now().isoformat(),
            "observacao": "Teste de check-in",
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["aluno_id"] == 1


def test_checkout_aluno():
    client = TestClient(app)
    duracao = random.randint(
        25, 120
    )  # Duração aleatória entre 25 e 120 minutos
    response = client.put(
        "/aluno/checkout",
        json={
            "aluno_id": 1,
            "data_saida": (
                datetime.now() + timedelta(minutes=duracao)
            ).isoformat(),
            "duracao": duracao,
            "observacao": "Teste de check-out",
        },
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()["aluno_id"] == 1


def test_processar_entrada_em_lote():
    """Teste para verificar o processamento de entrada em lote"""
    # Mock para o banco de dados
    mock_db = MagicMock()

    # Dados de teste
    aluno_id = 1
    data = datetime.now()

    # Executar a função
    resultado = processar_entrada(mock_db, aluno_id, data)

    # Verificar resultados
    assert resultado is True
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


def test_processar_saida_em_lote_sucesso():
    """Teste para verificar o processamento de saída em lote (sucesso)"""
    # Mock para o banco de dados
    mock_db = MagicMock()

    # Mock para o resultado da consulta
    mock_checkin = MagicMock()
    mock_checkin.data_entrada = datetime.now() - timedelta(
        hours=1
    )  # 1 hora atrás
    mock_db.query().filter().order_by().first.return_value = mock_checkin

    # Dados de teste
    aluno_id = 1
    data = datetime.now()

    # Executar a função
    resultado = processar_saida(mock_db, aluno_id, data)

    # Verificar resultados
    assert resultado is True
    assert mock_checkin.data_saida == data
    assert (
        mock_checkin.duracao
        == (data - mock_checkin.data_entrada).total_seconds() / 60
    )
    mock_db.commit.assert_called_once()


def test_processar_saida_em_lote_sem_checkin():
    """Teste para verificar o processamento de saída em lote (sem check-in aberto)"""
    # Mock para o banco de dados
    mock_db = MagicMock()

    # Mock para retornar None na consulta (sem check-in aberto)
    mock_db.query().filter().order_by().first.return_value = None

    # Dados de teste
    aluno_id = 1
    data = datetime.now()

    # Executar a função
    resultado = processar_saida(mock_db, aluno_id, data)

    # Verificar resultados
    assert resultado is False
    mock_db.commit.assert_not_called()


def test_obter_data_evento_com_timestamp():
    """Teste para verificar obtenção de data a partir de timestamp"""
    # Dados de teste
    timestamp = "2025-04-06T10:30:00"
    expected = datetime(2025, 4, 6, 10, 30)

    # Executar a função
    result = obter_data_evento(timestamp)

    # Verificar resultados
    assert result == expected


def test_obter_data_evento_sem_timestamp():
    """Teste para verificar obtenção de data atual quando não há timestamp"""
    # Executar a função
    before = datetime.now()
    result = obter_data_evento(None)
    after = datetime.now()

    # Verificar se o resultado está entre before e after
    assert before <= result <= after


@patch("challenge.rabbitmq.consumers.batch_checkin_consumer.next")
@patch("challenge.rabbitmq.consumers.batch_checkin_consumer.get_db")
@patch("challenge.rabbitmq.consumers.batch_checkin_consumer.validar_aluno")
def test_processar_checkin_em_lote_entrada(
    mock_validar_aluno, mock_get_db, mock_next
):
    """Teste para verificar processamento de mensagem de check-in em lote (entrada)"""
    # Configurar mocks
    mock_db = MagicMock()
    mock_next.return_value = mock_db
    mock_get_db.return_value = iter([mock_db])
    mock_validar_aluno.return_value = True

    # Criar channel e method mocks
    mock_channel = MagicMock()
    mock_method = MagicMock()
    mock_method.delivery_tag = "tag123"

    # Dados de teste
    data = {
        "aluno_id": 1,
        "tipo": "entrada",
        "timestamp": datetime.now().isoformat(),
    }
    body = json.dumps(data).encode()

    # Executar a função
    with patch(
        "challenge.rabbitmq.consumers.batch_checkin_consumer.processar_entrada"
    ) as mock_processar:
        processar_checkin_em_lote(mock_channel, mock_method, None, body)

        # Verificar resultado
        mock_processar.assert_called_once()
        mock_channel.basic_ack.assert_called_once_with(
            delivery_tag=mock_method.delivery_tag
        )


@patch("challenge.rabbitmq.consumers.batch_checkin_consumer.next")
@patch("challenge.rabbitmq.consumers.batch_checkin_consumer.get_db")
@patch("challenge.rabbitmq.consumers.batch_checkin_consumer.validar_aluno")
def test_processar_checkin_em_lote_saida(
    mock_validar_aluno, mock_get_db, mock_next
):
    """Teste para verificar processamento de mensagem de check-in em lote (saída)"""
    # Configurar mocks
    mock_db = MagicMock()
    mock_next.return_value = mock_db
    mock_get_db.return_value = iter([mock_db])
    mock_validar_aluno.return_value = True

    # Criar channel e method mocks
    mock_channel = MagicMock()
    mock_method = MagicMock()
    mock_method.delivery_tag = "tag456"

    # Dados de teste
    data = {
        "aluno_id": 1,
        "tipo": "saida",
        "timestamp": datetime.now().isoformat(),
    }
    body = json.dumps(data).encode()

    # Executar a função
    with patch(
        "challenge.rabbitmq.consumers.batch_checkin_consumer.processar_saida"
    ) as mock_processar:
        processar_checkin_em_lote(mock_channel, mock_method, None, body)

        # Verificar resultado
        mock_processar.assert_called_once()
        mock_channel.basic_ack.assert_called_once_with(
            delivery_tag=mock_method.delivery_tag
        )


@patch("challenge.rabbitmq.consumers.batch_checkin_consumer.next")
@patch("challenge.rabbitmq.consumers.batch_checkin_consumer.get_db")
@patch("challenge.rabbitmq.consumers.batch_checkin_consumer.validar_aluno")
def test_processar_checkin_em_lote_aluno_invalido(
    mock_validar_aluno, mock_get_db, mock_next
):
    """Teste para verificar processamento de mensagem com aluno inválido"""
    # Configurar mocks
    mock_db = MagicMock()
    mock_next.return_value = mock_db
    mock_get_db.return_value = iter([mock_db])
    mock_validar_aluno.return_value = False  # Aluno inválido

    # Criar channel e method mocks
    mock_channel = MagicMock()
    mock_method = MagicMock()
    mock_method.delivery_tag = "tag789"

    # Dados de teste
    data = {
        "aluno_id": 999,  # ID inválido
        "tipo": "entrada",
        "timestamp": datetime.now().isoformat(),
    }
    body = json.dumps(data).encode()

    # Executar a função
    with patch(
        "challenge.rabbitmq.consumers.batch_checkin_consumer.processar_entrada"
    ) as mock_processar:
        processar_checkin_em_lote(mock_channel, mock_method, None, body)

        # Verificar resultado - não deve chamar processar_entrada
        mock_processar.assert_not_called()
        # Mas deve confirmar a mensagem (ack)
        mock_channel.basic_ack.assert_called_once_with(
            delivery_tag=mock_method.delivery_tag
        )


@patch("challenge.rabbitmq.consumers.batch_checkin_consumer.next")
@patch("challenge.rabbitmq.consumers.batch_checkin_consumer.get_db")
def test_processar_checkin_em_lote_erro(mock_get_db, mock_next):
    """Teste para verificar tratamento de erro no processamento"""
    # Configurar mock para lançar exceção
    mock_next.side_effect = Exception("Erro de teste")
    mock_get_db.return_value = iter([MagicMock()])

    # Criar channel e method mocks
    mock_channel = MagicMock()
    mock_method = MagicMock()
    mock_method.delivery_tag = "tag000"

    # Dados de teste
    data = {
        "aluno_id": 1,
        "tipo": "entrada",
        "timestamp": datetime.now().isoformat(),
    }
    body = json.dumps(data).encode()

    # Executar a função
    processar_checkin_em_lote(mock_channel, mock_method, None, body)

    # Verificar resultado - deve rejeitar a mensagem para reprocessamento
    mock_channel.basic_nack.assert_called_once_with(
        delivery_tag=mock_method.delivery_tag, requeue=True
    )


# def test_ciclo_checkin_checkout_batch():
#     """Teste que simula um ciclo completo de check-in e check-out em lote"""
#     client = TestClient(app)

#     # 1. Cria um check-in via API
#     aluno_id = 1
#     data_entrada = datetime.now()
#     response = client.post(
#         "/aluno/checkin",
#         json={
#             "aluno_id": aluno_id,
#             "data_entrada": data_entrada.isoformat(),
#             "observacao": "Check-in para teste batch",
#         },
#     )
#     assert response.status_code == HTTPStatus.CREATED
#     checkin_id = response.json().get("id")

#     # 2. Simula o processamento em lote que seria feito pelo RabbitMQ
#     with patch(
#         "challenge.rabbitmq.consumers.batch_checkin_consumer.get_db"
#     ) as mock_get_db:
#         # Configura mocks para o banco
#         mock_db = MagicMock()
#         mock_get_db.return_value = iter([mock_db])

#         # Mock do aluno e check-in
#         mock_aluno = MagicMock()
#         mock_aluno.id = aluno_id
#         mock_db.query().filter().first.return_value = mock_aluno

#         mock_checkin = MagicMock()
#         mock_checkin.id = checkin_id
#         mock_checkin.aluno_id = aluno_id
#         mock_checkin.data_entrada = data_entrada
#         mock_db.query().filter().order_by().first.return_value = mock_checkin

#         # Simula o processamento de uma saída em lote
#         data_saida = data_entrada + timedelta(hours=1)
#         # duracao = 60  # 60 minutos

#         # Mock da chamada de processamento
#         with patch(
#             "challenge.rabbitmq.consumers.batch_checkin_consumer.processar_saida"
#         ) as mock_processar_saida:
#             mock_processar_saida.return_value = True

#             # Criar mensagem para saída
#             data = {
#                 "aluno_id": aluno_id,
#                 "tipo": "saida",
#                 "timestamp": data_saida.isoformat(),
#             }
#             body = json.dumps(data).encode()

#             # Mock do canal RabbitMQ
#             mock_channel = MagicMock()
#             mock_method = MagicMock()

#             # Processar a mensagem
#             processar_checkin_em_lote(mock_channel, mock_method, None, body)

#             # Verificar que a saída foi processada
#             mock_processar_saida.assert_called_once()
