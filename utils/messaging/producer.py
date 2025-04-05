import pika
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

RABBITMQ_HOST = "localhost"
CHECKIN_QUEUE_NAME = "checkin_queue"

def send_to_checkin_queue(message: dict):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
        channel = connection.channel()

        channel.queue_declare(queue=CHECKIN_QUEUE_NAME, durable=True)

        channel.basic_publish(
            exchange="",
            routing_key=CHECKIN_QUEUE_NAME,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2, # torna persistente
            )
        )
        logging.info(f"Mensagem enviada para a fila '{CHECKIN_QUEUE_NAME}': {message}")
        connection.close()
        return True
    except pika.exceptions.AMQPConnectionError as conn_error:
        logging.error(f"Erro ao conectar/publicar no RabbitMQ ({RABBITMQ_HOST}): {conn_error}")
        return False
    except Exception as e:
        logging.error(f"Erro inesperado ao enviar para a fila '{CHECKIN_QUEUE_NAME}': {e}")
        return False