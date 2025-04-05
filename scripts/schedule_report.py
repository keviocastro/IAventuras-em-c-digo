import pika
import json
import datetime
import logging
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

RABBITMQ_HOST = "localhost"
REPORT_QUEUE_NAME = "report_queue"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def schedule_daily_report():
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
        channel = connection.channel()

        channel.queue_declare(queue=REPORT_QUEUE_NAME, durable=True)

        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        report_date_str = yesterday.isoformat()
        message = {
            "report_date": report_date_str
        }

        channel.basic_publish(
            exchange='',
            routing_key=REPORT_QUEUE_NAME,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,
            )
        )
        logging.info(f"Mensagem para gerar relatório de {report_date_str} enviada para a fila '{REPORT_QUEUE_NAME}'.")
        connection.close()

    except pika.exceptions.AMQPConnectionError as conn_error:
        logging.error(f"Erro ao conectar/publicar no RabbitMQ para agendar relatório: {conn_error}")
    except Exception as e:
        logging.exception(f"Erro inesperado ao agendar relatório: {e}")

if __name__ == "__main__":
    logging.info("Executando agendador de relatório diário...")
    schedule_daily_report()
    logging.info("Agendador de relatório diário concluído.")






