import pika
import json
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
import pickle
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
# Função para atualizar o modelo de churn
# ---------------------------
def atualizar_modelo():
    print("🧠 Coletando dados de frequência e plano...")
    con = get_connection()

    # ---------------------------
    # Consulta com métricas por aluno
    # ---------------------------
    query = """
            SELECT 
                a.id AS aluno_id,
                a.plano_id,
                MAX(c.data_checkin) AS ultimo_checkin,
                COUNT(*) FILTER (
                    WHERE c.data_checkin >= NOW() - INTERVAL '28 days' AND c.duracao IS NOT NULL
                ) / 4.0 AS freq_semanal,
                AVG(EXTRACT(EPOCH FROM c.duracao)/60.0) FILTER (
                    WHERE c.duracao IS NOT NULL
                ) AS duracao_media
            FROM alunos a
            LEFT JOIN checkins c ON a.id = c.aluno_id
            GROUP BY a.id, a.plano_id
    """
    df = pd.read_sql_query(query, con)
    con.close()

    # ---------------------------
    # Tratamento de dados
    # ---------------------------
    df["dias_sem_checkin"] = (datetime.now() - df["ultimo_checkin"]).dt.days.fillna(999)
    df["freq_semanal"] = df["freq_semanal"].fillna(0)
    df["duracao_media"] = df["duracao_media"].fillna(0)

    # ---------------------------
    # Variável alvo: churn
    # ---------------------------
    df["churn"] = df["dias_sem_checkin"].apply(lambda d: 1 if d > 15 else 0)

    # ---------------------------
    # Seleção de variáveis preditoras
    # ---------------------------
    X = df[["dias_sem_checkin", "freq_semanal", "duracao_media", "plano_id"]]
    y = df["churn"]

    print("🤖 Treinando modelo de churn com múltiplas variáveis...")

    # ---------------------------
    # Codificação de plano_id e treinamento
    # ---------------------------
    X_encoded = pd.get_dummies(X, columns=["plano_id"])

    modelo = Pipeline([
        ("clf", RandomForestClassifier(n_estimators=100, random_state=42))
    ])

    modelo.fit(X_encoded, y)

    # ---------------------------
    # Salvando o modelo treinado
    # ---------------------------
    if not os.path.exists("modelos"):
        os.makedirs("modelos")

    with open("modelos/modelo_churn.pkl", "wb") as f:
        pickle.dump(modelo, f)

    print("✅ Modelo de churn atualizado com sucesso.")

# ---------------------------
# Callback do consumidor da fila
# ---------------------------
def callback(ch, method, properties, body):
    print("🧠 Atualizando modelo de churn com base nos dados reais...")
    atualizar_modelo()
    ch.basic_ack(delivery_tag=method.delivery_tag)

# ---------------------------
# Conexão com RabbitMQ
# ---------------------------
connection = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
channel = connection.channel()

channel.queue_declare(queue="fila_churn", durable=True)
channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue="fila_churn", on_message_callback=callback)

print("🎧 Aguardando mensagens para atualizar modelo de churn...")
channel.start_consuming()
