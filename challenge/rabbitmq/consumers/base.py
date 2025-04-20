import pika
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from infraestructure.channel import ChannelRabbitMQ


def solicitar_relatorio(data, connection=None, close_connection=True):
    """
    Solicita a geração de um relatório enviando um evento para o RabbitMQ

    Args:
        data: Data para a qual o relatório deve ser gerado
        connection: Conexão com RabbitMQ (opcional)
        close_connection: Se True, fecha a conexão após enviar (default: True)

    Returns:
        None
    """
    # Criar instância do gerenciador de canal
    channel_manager = ChannelRabbitMQ(connection)
    channel = channel_manager.get_channel()

    # Garantir que o exchange existe
    channel.exchange_declare(
        exchange="academia.eventos", exchange_type="direct", durable=True
    )

    mensagem = {"data": data, "tipo_relatorio": "frequencia_diaria"}

    channel.basic_publish(
        exchange="academia.eventos",
        routing_key="relatorio",
        body=json.dumps(mensagem),
        properties=pika.BasicProperties(
            delivery_mode=2,
        ),
    )

    # Só fecha a conexão se foi criada localmente ou se explicitamente solicitado
    if channel_manager.is_local_connection or close_connection:
        channel_manager.close()
