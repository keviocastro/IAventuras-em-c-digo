import pika
import json
import logging
import datetime
import os
import sys
from config.project_constants import EnvVars

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)


env = EnvVars()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

RABBITMQ_HOST = "localhost"
MODEL_UPDATE_QUEUE = "model_update_queue"

def schedule_model_update(force_update=False, data_path=None):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
        channel = connection.channel()
        
        channel.queue_declare(queue=MODEL_UPDATE_QUEUE, durable=True)
        
        message = {
            "timestamp": datetime.datetime.now().isoformat(),
            "force_update": force_update,
            "data_path": data_path or "data/num.csv"  # usa os dados padrão, mas pode ser alterado
        }
        
        channel.basic_publish(
            exchange='',
            routing_key=MODEL_UPDATE_QUEUE,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,
            )
        )
        
        logging.info(f"Solicitação de atualização do modelo enfileirada: {message}")
        connection.close()
        return True
        
    except pika.exceptions.AMQPConnectionError as conn_error:
        logging.error(f"Erro ao conectar ao RabbitMQ: {conn_error}")
        return False
    except Exception as e:
        logging.exception(f"Erro inesperado ao agendar atualização do modelo: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Agenda uma atualização do modelo de churn.')
    parser.add_argument('--force', action='store_true', help='Força a atualização do modelo')
    parser.add_argument('--data', type=str, help='Caminho para dados específicos', default=None)
    
    args = parser.parse_args()
    
    success = schedule_model_update(force_update=args.force, data_path=args.data)
    
    if success:
        print("Solicitação de atualização do modelo enviada com sucesso.")
    else:
        print("Falha ao enviar solicitação de atualização.")


