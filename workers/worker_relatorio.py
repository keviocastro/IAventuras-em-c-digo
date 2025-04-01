import pika
import json
import psycopg2
import pandas as pd
from datetime import datetime
import os

# Caminho absoluto até o banco.json na pasta anterior
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "banco.json")

# ---------------------------
# Configuração do banco
# ---------------------------
with open(config_path, "r") as f:
    db_config = json.load(f)

def get_connection():
    return psycopg2.connect(**db_config)

# ---------------------------
# Função principal de geração de relatórios
# ---------------------------
def gerar_relatorio():
    con = get_connection()
    query = """
        SELECT a.id AS aluno_id, a.nome, c.data_checkin
        FROM checkins c
        JOIN alunos a ON a.id = c.aluno_id
        WHERE c.data_checkin::date = CURRENT_DATE
        ORDER BY c.data_checkin DESC
    """
    df = pd.read_sql_query(query, con)
    con.close()

    if not os.path.exists("relatorios"):
        os.makedirs("relatorios")

    nome_arquivo = f"relatorios/relatorio_frequencia_{datetime.now().strftime('%Y%m%d')}.csv"
    df.to_csv(nome_arquivo, index=False)
    print(f"✔️ Relatório gerado: {nome_arquivo}")

# ---------------------------
# Callback da fila
# ---------------------------
def callback(ch, method, properties, body):
    print(f"📊 Gerando relatório diário de frequência...")
    gerar_relatorio()
    ch.basic_ack(delivery_tag=method.delivery_tag)

connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()

channel.queue_declare(queue="fila_relatorio", durable=True)
channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue="fila_relatorio", on_message_callback=callback)

print("🎧 Aguardando mensagens para gerar relatórios...")
channel.start_consuming()
