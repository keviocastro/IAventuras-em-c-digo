import pika
import json
import psycopg2
from datetime import datetime
import os

# ---------------------------
# Configuração do banco
# ---------------------------
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "banco.json")
with open(config_path, "r") as f:
    db_config = json.load(f)

def get_connection():
    return psycopg2.connect(**db_config)

# ---------------------------
# Função principal de processamento
# ---------------------------
def processar_checkins_reais(payload):
    alunos = payload.get("alunos", [])
    data_checkin = payload.get("data_checkin")

    if not alunos:
        print("⚠️ Nenhum aluno enviado na mensagem.")
        return

    if not data_checkin:
        data_checkin = datetime.now()
    else:
        data_checkin = datetime.fromisoformat(data_checkin)

    con = get_connection()
    cur = con.cursor()

    for aluno_id in alunos:
        cur.execute("INSERT INTO checkins (aluno_id, data_checkin) VALUES (%s, %s)", (aluno_id, data_checkin))

    con.commit()
    cur.close()
    con.close()
    print(f"✅ {len(alunos)} check-ins registrados com sucesso em {data_checkin}.")

# ---------------------------
# Callback da fila
# ---------------------------
def callback(ch, method, properties, body):
    print("📦 Mensagem recebida para processar check-ins reais.")
    try:
        payload = json.loads(body)
        processar_checkins_reais(payload)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"❌ Erro ao processar mensagem: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag)

# ---------------------------
# Conexão com RabbitMQ
# ---------------------------
connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()

channel.queue_declare(queue="fila_checkin", durable=True)
channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue="fila_checkin", on_message_callback=callback)

print("🎧 Aguardando mensagens para check-ins reais...")
channel.start_consuming()
