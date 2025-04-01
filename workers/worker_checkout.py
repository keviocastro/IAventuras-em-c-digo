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
# Função principal de processamento de checkouts
# ---------------------------
def processar_checkouts(payload):
    alunos = payload.get("alunos", [])

    if not alunos:
        print("⚠️ Nenhum aluno enviado na mensagem.")
        return

    con = get_connection()
    cur = con.cursor()

    atualizados = 0
    for aluno_id in alunos:
        cur.execute("""
            UPDATE checkins
            SET data_checkout = CURRENT_TIMESTAMP
            WHERE id = (
                SELECT id FROM checkins
                WHERE aluno_id = %s AND data_checkout IS NULL
                ORDER BY data_checkin DESC
                LIMIT 1
            )
        """, (aluno_id,))
        atualizados += cur.rowcount

    con.commit()
    cur.close()
    con.close()
    print(f"✅ {atualizados} checkouts registrados com sucesso.")

# ---------------------------
# Callback da fila
# ---------------------------
def callback(ch, method, properties, body):
    print("📦 Mensagem recebida para processar checkouts...")
    try:
        payload = json.loads(body)
        processar_checkouts(payload)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"❌ Erro ao processar mensagem: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag)

# ---------------------------
# Conexão com RabbitMQ
# ---------------------------
connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()

channel.queue_declare(queue="fila_checkout", durable=True)
channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue="fila_checkout", on_message_callback=callback)

print("🎧 Aguardando mensagens para processar checkouts...")
channel.start_consuming()
