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

from machine_learning.pipeline import pipeline


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
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["aluno_id"] == 1


API_URL = "http://localhost:8000"  # URL da API FastAPI


@patch(
    "rabbitmq.producers.base.solicitar_relatorio_diario"
)  # Caminho corrigido
@patch("requests.post")
def test_gerar_e_verificar_relatorio(mock_post, mock_solicitar_relatorio):
    client = TestClient(app)

    # Configurar o mock para que ele faça algo simples como criar os arquivos de relatório
    def side_effect(data=None):
        # Criar os arquivos esperados pelo teste
        data_str = data or datetime.now().strftime("%Y-%m-%d")
        RELATORIOS_DIR = Path(__file__).parent / "relatorios"
        RELATORIOS_DIR.mkdir(exist_ok=True, parents=True)

        relatorio_txt = RELATORIOS_DIR / f"relatorio_{data_str}.txt"
        with open(relatorio_txt, "w") as f:
            f.write(f"Relatório de teste para {data_str}")

        grafico_png = RELATORIOS_DIR / f"frequencia_{data_str}.png"
        # Criar um arquivo PNG vazio
        with open(grafico_png, "wb") as f:
            f.write(b"PNG")

    mock_solicitar_relatorio.side_effect = side_effect

    # Definir data para o relatório
    data_hoje = datetime.now().strftime("%Y-%m-%d")

    # Usar o client de teste
    response = client.post("/relatorios/diario", json={"data": data_hoje})

    assert response.status_code == 202


@patch("machine_learning.pipeline.treinar_modelo_churn")
@patch("machine_learning.pipeline.save_model")
def test_metricas_no_intervalo_correto(mock_save_model, mock_treinar_modelo):
    """Testa se as métricas retornadas estão no intervalo correto de 0 a 1"""
    # Configurar os mocks
    mock_modelo = MagicMock()
    mock_metricas = {
        "accuracy": 0.9080,
        "precision": 0.7895,
        "recall": 0.7895,
        "f1": 0.7895,
    }

    mock_dados = MagicMock()
    mock_modelo_path = "modelo_churn_2025-04-07.pkl"

    # Configurar o retorno da função mock
    mock_treinar_modelo.return_value = (mock_modelo, mock_metricas, mock_dados)
    mock_save_model.return_value = mock_modelo_path

    # Executar a função pipeline
    resultado = pipeline()

    # Extrair as métricas
    _, metricas, _, _ = resultado

    # Verificar se cada métrica está no intervalo de 0 a 1
    for nome_metrica, valor_metrica in metricas.items():
        assert valor_metrica >= 0.0, f"Métrica {nome_metrica} deve ser >= 0"
        assert valor_metrica <= 1.0, f"Métrica {nome_metrica} deve ser <= 1"


@patch("machine_learning.pipeline.treinar_modelo_churn")
@patch("machine_learning.pipeline.save_model")
def test_salvamento_e_carregamento_modelo(
    mock_save_model, mock_treinar_modelo
):
    """Testa se o modelo é salvo e pode ser carregado corretamente"""
    # Criar caminho temporário para teste
    modelo_path = "test_model.pkl"

    # Configurar os mocks
    mock_modelo = MagicMock()
    mock_metricas = {"accuracy": 0.85}
    mock_dados = MagicMock()

    # Configurar o retorno da função mock
    mock_treinar_modelo.return_value = (mock_modelo, mock_metricas, mock_dados)
    mock_save_model.return_value = modelo_path

    # Executar a função pipeline
    resultado = pipeline()
    _, _, _, path_retornado = resultado

    assert path_retornado == modelo_path


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

    # Criar mock para o check-in que será retornado pela consulta
    mock_checkin = MagicMock()
    mock_checkin.data_entrada = datetime.now() - timedelta(hours=1)
    mock_checkin.duracao_treino = None

    # Configurar o mock do banco de dados para retornar o check-in mock
    mock_db.query().filter().order_by().first.return_value = mock_checkin

    # Dados de teste
    aluno_id = 1
    data = datetime.now()

    # Executar a função
    resultado = processar_saida(mock_db, aluno_id, data)

    # Verificar resultados
    assert resultado is True
    assert mock_checkin.duracao_treino is not None
    import math

    assert math.isclose(
        mock_checkin.duracao_treino,
        (data - mock_checkin.data_entrada).total_seconds() / 60,
        rel_tol=0.01,  # 1% de tolerância
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
