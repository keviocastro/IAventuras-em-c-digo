import pika, json
from app.database import SessionLocal
from app.models import checkins
from datetime import datetime

def gerar_relatorio(data_str):
    db = SessionLocal()
    try:
        data_date = datetime.strptime(data_str, "%Y-%m-%d").date()
        result = db.query(checkins).filter(checkins.data == data_date).all()
        print(f"Relatório de {data_str}: {result}")
    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")
    finally:
        db.close()

def callback(ch, method, properties, body):
    try:
        payload = json.loads(body.decode())
        if payload.get("action") == "gerar_relatorio":
            data = payload.get("data")
            gerar_relatorio(data)
    except Exception as e:
        print(f"Erro: {e}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consumer():
    credentials = pika.PlainCredentials("admin", "admin123")
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue='relatorio', durable=True)
    print(" [*] Aguardando mensagens de relatório. Para sair pressione CTRL+C")
    channel.basic_consume(queue='relatorio', on_message_callback=callback)
    channel.start_consuming()

if __name__ == "__main__":
    start_consumer()