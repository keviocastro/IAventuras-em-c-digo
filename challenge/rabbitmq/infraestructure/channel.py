import pika

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from connection import ConnectionRabbitMQ


class ChannelRabbitMQ:
    """
    Classe para gerenciar o canal RabbitMQ.
    """

    def __init__(self, connection=None):
        self.connection = (
            connection or ConnectionRabbitMQ().get_rabbitmq_connection()
        )
        self.channel = self.connection.channel()
        self.local_connection = connection is None

    def close(self):
        """
        Fecha a conexão com o RabbitMQ.
        """
        try:
            if self.channel and self.channel.is_open:
                self.channel.close()
        except pika.exceptions.ChannelClosedByBroker as e:
            return f"Erro ao fechar canal: {e}"

    def get_channel(self):
        """
        Retorna o canal RabbitMQ.
        """
        return self.channel

    @property
    def is_local_connection(self):
        """
        Retorna se a conexão foi criada localmente.
        """
        return self.local_connection
