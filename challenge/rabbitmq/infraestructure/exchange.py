import pika
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from channel import ChannelRabbitMQ


class ExchangeRabbitMQ:
    """
    Classe para gerenciar o exchange RabbitMQ.
    """

    def __init__(self, connection=None):
        self.channel_manager = ChannelRabbitMQ(connection)
        self.channel = self.channel_manager.get_channel()

    def declare_exchange(self, exchange_name, exchange_type="direct"):
        """
        Declara um exchange no RabbitMQ.

        Args:
            exchange_name: Nome do exchange a ser declarado.
            exchange_type: Tipo do exchange (default: "direct").
        """
        try:
            self.channel.exchange_declare(
                exchange=exchange_name,
                exchange_type=exchange_type,
                durable=True,
            )
        except pika.exceptions.ChannelClosedByBroker as e:
            return f"Erro ao declarar exchange: {e}"

    def publish_message(self, exchange_name, routing_key, message):
        """
        Publica uma mensagem em um exchange RabbitMQ.

        Args:
            exchange_name: Nome do exchange onde a mensagem será publicada.
            routing_key: Chave de roteamento para a mensagem.
            message: Mensagem a ser publicada (dicionário).
        """
        try:
            self.channel.basic_publish(
                exchange=exchange_name,
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # torna a mensagem persistente
                ),
            )
        except pika.exceptions.ChannelClosedByBroker as e:
            return f"Erro ao publicar mensagem: {e}"

    def close_connection(self):
        """
        Fecha a conexão com o RabbitMQ.
        """
        self.channel_manager.close()

    @property
    def is_local_connection(self):
        """
        Verifica se a conexão é local.
        """
        return self.channel_manager.is_local_connection
