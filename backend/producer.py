import pika, os, json

def publish_checkin(aluno_id):
    url = os.getenv('RABBITMQ_URL')
    params = pika.URLParameters(url)
    conn = pika.BlockingConnection(params)
    ch = conn.channel()

    ch.queue_declare(queue='checkins')
    ch.basic_publish(
        exchange='',
        routing_key='checkins',
        body=json.dumps({'aluno_id': aluno_id})
    )
    conn.close()
