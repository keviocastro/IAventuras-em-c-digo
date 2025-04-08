from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from infraestructure.exchange import ExchangeRabbitMQ
from datetime import datetime


def publicar_checkin_ou_checkout(
    aluno_id, timestamp, connection=None, fechar_conexao=True, entrada=True
):
    """
    Publica um evento de check-in no RabbitMQ

    Args:
        aluno_id: ID do aluno que realizou o check-in
        timestamp: Data e hora do check-in
        connection: Conexão com RabbitMQ (opcional)
        fechar_conexao: Se True, fecha a conexão após enviar (default: True)
        entrada: Se True, é um check-in; se False, é um check-out

    Returns:
        None
    """

    exchange = ExchangeRabbitMQ(connection)
    exchange.declare_exchange("academia.eventos", "direct")

    mensagem = {
        "aluno_id": aluno_id,
        "timestamp": timestamp or None,
        "tipo": "entrada" if entrada else "saida",
    }

    exchange.publish_message(
        "academia.eventos",
        "checkin",
        mensagem,  # Removido as chaves {} que estavam transformando em conjunto
    )

    # Só fecha a conexão se foi criada localmente ou se explicitamente solicitado
    if exchange.is_local_connection or fechar_conexao:
        exchange.close_connection()


def publicar_checkins_em_massa(checkins, connection=None, fechar_conexao=True):
    """
    Publica múltiplos check-ins de uma vez no RabbitMQ

    Args:
        checkins: Lista de dicionários com aluno_id, timestamp e tipo
        connection: Conexão com RabbitMQ (opcional)
        fechar_conexao: Se True, fecha a conexão após enviar (default: True)

    Returns:
        None
    """
    exchange = ExchangeRabbitMQ(connection)
    exchange.declare_exchange("academia.eventos", "direct")

    for checkin in checkins:
        exchange.publish_message("academia.eventos", "checkin.batch", checkin)

    if exchange.is_local_connection or fechar_conexao:
        exchange.close_connection()


def solicitar_relatorio_diario(
    data=None, connection=None, fechar_conexao=True
):
    """
    Solicita a geração de um relatório diário de frequência

    Args:
        data: Data para o relatório (formato ISO), se None usa a data atual
        connection: Conexão com RabbitMQ (opcional)
        fechar_conexao: Se True, fecha a conexão após enviar (default: True)

    Returns:
        None
    """
    exchange = ExchangeRabbitMQ(connection)
    exchange.declare_exchange("academia.eventos", "direct")

    mensagem = {
        "data": data or datetime.now().date().isoformat(),
        "tipo": "relatorio_diario",
    }

    exchange.publish_message("academia.eventos", "relatorio", mensagem)

    if exchange.is_local_connection or fechar_conexao:
        exchange.close_connection()


def solicitar_atualizacao_modelo_churn(connection=None, fechar_conexao=True):
    """
    Solicita a atualização do modelo de previsão de churn

    Args:
        connection: Conexão com RabbitMQ (opcional)
        fechar_conexao: Se True, fecha a conexão após enviar (default: True)

    Returns:
        None
    """
    exchange = ExchangeRabbitMQ(connection)
    exchange.declare_exchange("academia.eventos", "direct")

    mensagem = {
        "timestamp": datetime.now().isoformat(),
        "tipo": "atualizar_modelo",
    }

    exchange.publish_message("academia.eventos", "modelo", mensagem)

    if exchange.is_local_connection or fechar_conexao:
        exchange.close_connection()
