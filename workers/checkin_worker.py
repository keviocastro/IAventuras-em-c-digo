import pika
import json
import logging
import time
import sys
import os
from utils.db.crud import PostgreSQLDatabase
from config.project_constants import EnvVars
from config.project_constants import DatetimeFormats as dt

env = EnvVars()
db_password = env.get_var("DB_PASSWORD")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

RABBITMQ_HOST = "localhost"
CHECKIN_QUEUE_NAME = "checkin_queue"

db = PostgreSQLDatabase(
    user="juanml",
    dbname="churnml",
    password=db_password,
    host="localhost",
    port="5432"
)

def process_checkin_message(channel, method, properties, body):
    logging.info(f"Recebida mensagem bruta: {body}")
    try:
        message = json.loads(body.decode('utf-8'))
        aluno_id = message.get('id_aluno')
        timestamp_req = message.get('timestamp_requisicao', 'N/A')

        if aluno_id is None:
            logging.error("Mensagem recebida sem 'id_aluno'. Descartando.")
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return

        logging.info(f"Processando check-in para aluno ID: {aluno_id} (requisição de {timestamp_req})")

        if not db.connect_db(): # Use sua função de conexão
             logging.error("Erro ao conectar ao Banco de Dados. Mensagem será rejeitada e reenfileirada.")
             channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
             time.sleep(5)
             return

        try:
            db.insert(
                "checkins",
                {
                    "id_aluno": aluno_id,
                    "data_checkin": dt.get_datetime()
                }
            )
            db.close_db()
            logging.info(f"Check-in para aluno ID: {aluno_id} registrado no banco com sucesso.")

            channel.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as db_error:
            logging.error(f"Erro ao inserir check-in no DB para aluno ID: {aluno_id}. Erro: {db_error}")
            db.close_db()
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            time.sleep(5)

    except json.JSONDecodeError:
        logging.error(f"Erro ao decodificar JSON da mensagem: {body}")
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logging.exception(f"Erro inesperado ao processar mensagem: {e}")
        channel.basic_ack(delivery_tag=method.delivery_tag)

def main():
    connection = None
    while True:
        try:
            logging.info(f"Tentando conectar ao RabbitMQ em {RABBITMQ_HOST}...")
            connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
            channel = connection.channel()
            logging.info("Conectado ao RabbitMQ com sucesso!")

            channel.queue_declare(queue=CHECKIN_QUEUE_NAME, durable=True)
            logging.info(f"Declarada fila '{CHECKIN_QUEUE_NAME}'. Aguardando mensagens...")

            channel.basic_qos(prefetch_count=1)

            channel.basic_consume(
                queue=CHECKIN_QUEUE_NAME,
                on_message_callback=process_checkin_message
            )

            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as conn_err:
            logging.error(f"Falha na conexão com RabbitMQ: {conn_err}. Tentando reconectar em 10 segundos...")
            if connection and not connection.is_closed:
                try:
                    connection.close()
                except Exception as close_err:
                    logging.error(f"Erro ao fechar conexão antiga: {close_err}")
            time.sleep(10)
        except KeyboardInterrupt:
            logging.info("Consumidor interrompido manualmente.")
            if connection and not connection.is_closed:
                connection.close()
            break
        except Exception as general_err:
            logging.exception(f"Erro inesperado no consumidor: {general_err}. Reiniciando em 10 segundos...")
            if connection and not connection.is_closed:
                 try:
                    connection.close()
                 except Exception as close_err:
                    logging.error(f"Erro ao fechar conexão antiga: {close_err}")
            time.sleep(10)

if __name__ == "__main__":
    main()