import pika, time, json
from app.models import Aluno, checkins
from app.database import SessionLocal

def process_checkins(aluno_id: int, data_checkin: str, horario_checkin: str, horario_checkout: str):
    db = SessionLocal()
    try:
        aluno = db.query(Aluno).filter(Aluno.id == aluno_id).first()
        if aluno:
            checkin = checkins(
                aluno_id=aluno_id,
                data=data_checkin,
                horario_checkin=horario_checkin,
                horario_checkout=horario_checkout
            )
            db.add(checkin)
            db.commit()
            print(f"Check-in registrado para o aluno {aluno.nome} (ID: {aluno_id}) na data {data_checkin}.")
        else:
            print(f"Aluno com ID {aluno_id} não encontrado.")
    except Exception as e:
        print(f"Erro ao processar check-in: {e}")
    finally:
        db.close()

def callback(ch, method, properties, body):
    """Função chamada quando uma mensagem é recebida na fila."""
    try:
        payload = json.loads(body.decode())
        aluno_id = payload.get("aluno_id")
        data_checkin = payload.get("data", time.strftime("%Y-%m-%d"))
        horario_checkin = payload.get("horario_checkin")
        horario_checkout = payload.get("horario_checkout")
        print(f" [x] Recebido: aluno_id={aluno_id}, data={data_checkin}, horario_checkin={horario_checkin}, horario_checkout={horario_checkout}")
        process_checkins(aluno_id, data_checkin, horario_checkin, horario_checkout)
    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consumer():
    """Configura o consumidor RabbitMQ."""
    credentials = pika.PlainCredentials("admin", "admin123")
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue='checkins', durable=True)
    print(" [*] Esperando mensagens. Para sair, pressione CTRL+C")
    channel.basic_consume(queue='checkins', on_message_callback=callback)
    channel.start_consuming()

if __name__ == "__main__":
    start_consumer()