from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from infraestructure.connection import ConnectionRabbitMQ
from infraestructure.channel import ChannelRabbitMQ


def setup_rabbitmq():
    """
    Estabelecer conexão
    Como temos o RabbitMQ rodando localmente, podemos usar a conexão padrão
    """

    channel_manager = ChannelRabbitMQ()
    channel = channel_manager.get_channel()

    # Criar exchange
    channel.exchange_declare(
        exchange="academia.eventos", exchange_type="direct", durable=True
    )

    # Criar queues
    channel.queue_declare(queue="checkins.processamento", durable=True)
    channel.queue_declare(queue="relatorios.diarios", durable=True)
    channel.queue_declare(queue="modelo.churn", durable=True)
    channel.queue_declare(queue="checkins.batch", durable=True)

    # Criar bindings
    channel.queue_bind(
        exchange="academia.eventos",
        queue="checkins.processamento",
        routing_key="checkin",
    )

    channel.queue_bind(
        exchange="academia.eventos",
        queue="relatorios.diarios",
        routing_key="relatorio",
    )

    channel.queue_bind(
        exchange="academia.eventos", queue="modelo.churn", routing_key="modelo"
    )

    channel.queue_bind(
        exchange="academia.eventos",
        queue="checkins.batch",
        routing_key="checkin.batch",
    )

    print("RabbitMQ configurado com sucesso!")
    channel_manager.close()


if __name__ == "__main__":
    setup_rabbitmq()
