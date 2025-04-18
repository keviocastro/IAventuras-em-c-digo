import pika, json, os
from models import Session, Checkin
from datetime import datetime
def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        session = Session()

        existing_checkin = session.query(Checkin).filter_by(aluno_id=data['aluno_id']).order_by(Checkin.id.desc()).first()

        if existing_checkin and existing_checkin.checkout is None:
            existing_checkin.checkout = datetime.now()
        else:
            checkin = Checkin(aluno_id=data['aluno_id'], checkin=datetime.now())
            session.add(checkin)

        session.commit()
        session.close()

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")


def start_consumer():
    rabbit_url = os.getenv("RABBITMQ_URL")
    params = pika.URLParameters(rabbit_url)

    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue='checkins', durable=True)

    channel.basic_consume(queue='checkins', on_message_callback=callback, auto_ack=False)
    print("Consumer ouvindo fila 'checkins'...")
    channel.start_consuming()

