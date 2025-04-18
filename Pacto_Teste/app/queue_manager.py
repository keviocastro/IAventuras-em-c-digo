import pika, json
import sys

class QueueManager:
    def __init__(self, queue_name='checkins'):
        self.queue_name = queue_name
        credentials = pika.PlainCredentials("admin", "admin123")
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', credentials=credentials))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue_name, durable=True)
        print(" [*] Waiting for messages. To exit press CTRL+C")

    def publish_checkin(self, aluno_id: int, data: str, horario_checkin: str, horario_checkout: str):
        msg = json.dumps({
            "aluno_id": aluno_id,
            "data": data,
            "horario_checkin": horario_checkin,
            "horario_checkout": horario_checkout
        })
        self.channel.basic_publish(
            exchange='',
            routing_key=self.queue_name,
            body=msg,
            properties=pika.BasicProperties(
                delivery_mode=2, 
            )
        )
        print(f" [x] Sent check-in for aluno_id={aluno_id}")

    def publish_churn_update(self):
        msg = json.dumps({"action": "atualizar_churn"})
        self.channel.basic_publish(
            exchange='',
            routing_key='churn',
            body=msg,
            properties=pika.BasicProperties(delivery_mode=2) 
        )
        print(f"Payload enviado: {msg}")
        print(" [x] Mensagem de atualização de churn enviada.")
    
    def close(self):
        self.connection.close()
        print(" [*] Connection closed")