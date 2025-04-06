import pika
import json
import logging
import time
import sys
import os
import datetime

from utils.db.crud import PostgreSQLDatabase
from config.project_constants import EnvVars

env = EnvVars()
db_password = env.get_var("DB_PASSWORD")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

RABBITMQ_HOST = "localhost"
REPORT_QUEUE_NAME = "report_queue"

db = PostgreSQLDatabase(
    user="juanml",
    dbname="churnml",
    password=db_password,
    host="localhost",
    port="5432"
)

def generate_frequency_report(report_date_str: str):
    logging.info(f"Iniciando geração do relatório de frequência para a data: {report_date_str}")

    try:
        report_date = datetime.date.fromisoformat(report_date_str)
    except ValueError:
        logging.error(f"Formato de data inválido recebido: {report_date_str}. Esperado YYYY-MM-DD.")
        return False

    if not db.connect_db():
        logging.error("Falha ao conectar ao DB para gerar relatório.")
        return False

    try:
        query = """
        SELECT 
            a.nome_aluno,
            ci.data_checkin,
            co.data_checkout,
            p.nome_plano,
            m.data_inicio AS inicio_matricula,
            m.data_fim AS fim_matricula
        FROM checkins ci
        JOIN alunos a ON ci.id_aluno = a.id_aluno
        LEFT JOIN checkouts co ON co.id_aluno = ci.id_aluno
            AND co.data_checkout > ci.data_checkin
        LEFT JOIN matriculas m ON ci.id_aluno = m.id_aluno
            AND ci.data_checkin::DATE BETWEEN m.data_inicio AND COALESCE(m.data_fim, CURRENT_DATE)
        LEFT JOIN planos p ON m.id_plano = p.id_plano
        WHERE ci.data_checkin::DATE = %s
        ORDER BY ci.data_checkin DESC;
        """
        
        db.cursor.execute(query, (report_date,))
        checkins_data = db.cursor.fetchall()

        db.close_db()
        logging.info(f"Dados de frequência ({len(checkins_data)} registros) recuperados para {report_date_str}.")

        logging.info(f"--- Relatório de Frequência: {report_date_str} ---")
        if checkins_data:
            alunos_presentes = set(row[0] for row in checkins_data)
            logging.info(f"Total de Check-ins: {len(checkins_data)}")
            logging.info(f"Total de Alunos Únicos: {len(alunos_presentes)}")
        else:
            logging.info("Nenhum check-in registrado para esta data.")
        logging.info("--- Fim do Relatório ---")

        return True

    except Exception as e:
        logging.exception(f"Erro durante a consulta ao DB ou geração do relatório para {report_date_str}: {e}")
        db.close_db()
        return False

def process_report_message(channel, method, properties, body):
    logging.info(f"Recebida mensagem de solicitação de relatório: {body}")
    try:
        message = json.loads(body.decode('utf-8'))
        report_date_str = message.get('report_date')

        if not report_date_str:
            logging.error("Mensagem recebida sem 'report_date'. Descartando.")
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return

        success = generate_frequency_report(report_date_str)

        if success:
            logging.info(f"Processamento do relatório para {report_date_str} concluído com sucesso.")
            channel.basic_ack(delivery_tag=method.delivery_tag)
        else:
            logging.error(f"Falha ao gerar o relatório para {report_date_str}. Mensagem será descartada (não reenfileirada).")
            channel.basic_ack(delivery_tag=method.delivery_tag)

    except json.JSONDecodeError:
        logging.error(f"Erro ao decodificar JSON da mensagem: {body}")
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logging.exception(f"Erro inesperado ao processar mensagem de relatório: {e}")
        channel.basic_ack(delivery_tag=method.delivery_tag)

def main():
    connection = None
    while True:
        try:
            logging.info(f"Tentando conectar ao RabbitMQ em {RABBITMQ_HOST} para o worker de relatórios...")
            connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
            channel = connection.channel()
            logging.info("Conectado ao RabbitMQ com sucesso!")

            channel.queue_declare(queue=REPORT_QUEUE_NAME, durable=True)
            logging.info(f"Declarada fila '{REPORT_QUEUE_NAME}'. Aguardando mensagens...")

            channel.basic_qos(prefetch_count=1)

            channel.basic_consume(
                queue=REPORT_QUEUE_NAME,
                on_message_callback=process_report_message
            )

            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as conn_err:
            logging.error(f"Falha na conexão com RabbitMQ: {conn_err}. Tentando reconectar em 10 segundos...")
            if connection and not connection.is_closed: connection.close()
            time.sleep(10)
        except KeyboardInterrupt:
            logging.info("Consumidor de relatórios interrompido.")
            if connection and not connection.is_closed: connection.close()
            break
        except Exception as general_err:
            logging.exception(f"Erro inesperado no consumidor de relatórios: {general_err}. Reiniciando em 10 segundos...")
            if connection and not connection.is_closed: connection.close()
            time.sleep(10)

if __name__ == "__main__":
    main()


