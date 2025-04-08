import pika
from dotenv import load_dotenv
import os

load_dotenv()


class ConnectionRabbitMQ:
    """
    Classe para gerenciar a conexão com o RabbitMQ e criar canais.
    """

    def __init__(self, connection=None):
        self.connection = connection or self.get_rabbitmq_connection()

    # Função para obter conexão com RabbitMQ
    # Esta função carrega as variáveis de ambiente do arquivo .env e cria uma conexão com o RabbitMQ usando as credenciais fornecidas.
    def get_rabbitmq_connection(self):
        """
        Estabelece uma conexão com o RabbitMQ usando as credenciais e parâmetros definidos.

        Returns:
            pika.BlockingConnection: Conexão com o RabbitMQ.
        """

        username = os.environ.get("RABBITMQ_USERNAME", "guest")
        password = os.environ.get("RABBITMQ_PASSWORD", "guest")

        RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
        RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", "5672"))
        RABBITMQ_VHOST = os.environ.get("RABBITMQ_VHOST", "/")

        try:
            credentials = pika.PlainCredentials(
                username=username,
                password=password,
            )

            parameters = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                virtual_host=RABBITMQ_VHOST,
                credentials=credentials,
            )

            connection = pika.BlockingConnection(parameters)

        except pika.exceptions.AMQPConnectionError as e:
            raise Exception(f"Erro ao conectar ao RabbitMQ: {e}")
        except pika.exceptions.ChannelClosedByBroker as e:
            raise Exception(f"Erro ao criar canal: {e}")
        except Exception as e:
            raise Exception(f"Erro inesperado: {e}")

        return connection
