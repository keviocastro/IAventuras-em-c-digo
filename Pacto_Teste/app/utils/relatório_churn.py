import pika, json

def publish_churn_update():
    credentials = pika.PlainCredentials("admin", "admin123")
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue='churn', durable=True)
    msg = json.dumps({"action": "atualizar_churn"})
    channel.basic_publish(
        exchange='',
        routing_key='churn',
        body=msg,
        properties=pika.BasicProperties(delivery_mode=2)
    )
    print(" [x] Pedido de atualização de churn enviado")
    connection.close()