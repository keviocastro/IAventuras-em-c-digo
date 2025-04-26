import pika
import json
from academia.relatorio.utils import gerar_pdf_relatorio, enviar_relatorio_por_email
from academia import app, EMAIL_PARA_TESTE, RABBITMQ_URL
from datetime import datetime

def callback(ch, method, properties, body):
    dados = json.loads(body)
    checkins = dados['checkins']
    hoje = datetime.today().date() 
    gerar_pdf_relatorio(checkins, hoje)
    enviar_relatorio_por_email(EMAIL_PARA_TESTE, checkins, hoje)

def iniciar_worker_relatorio():
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.queue_declare(queue='relatorio_diario', durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='relatorio_diario', on_message_callback=callback)
    print(" [*] Aguardando mensagens...")
    channel.start_consuming()

 