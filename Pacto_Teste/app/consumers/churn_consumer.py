import pika, json
from app.database import SessionLocal
from app.models import Aluno
import pandas as pd
from app.churn_model import calcular_features
import joblib
import time
from app.consumers.consumer import process_checkins  # Substitua pelo módulo correto


def calcular_risco_churn():
    db = SessionLocal()
    try:

        # Carregua o modelo pré-treinado
        model = joblib.load("churn_model.pkl")
        print("Modelo de churn carregado com sucesso.")

        alunos = db.query(Aluno).all()

        data = calcular_features(db, alunos)

        df = pd.DataFrame(data, columns=['frequencia_semanal', 'tempo_ultimo_checkin', 'duracao_media_visitas', 'tipo_plano'])

        riscos = model.predict(df)

        # Atualiza os alunos com o risco de churn
        for aluno, risco in zip(alunos, riscos):
            aluno.risco_churn = risco  
            db.add(aluno) 
        db.commit()  
        print("Risco de churn atualizado para todos os alunos.")
    except Exception as e:
        print(f"Erro ao calcular risco de churn: {e}")
    finally:
        db.close()

def callback(ch, method, properties, body):
    try:
        payload = json.loads(body.decode())
        aluno_id = payload.get("aluno_id")
        data_checkin = payload.get("data", time.strftime("%Y-%m-%d"))
        horario_checkin = payload.get("horario_checkin", None)
        horario_checkout = payload.get("horario_checkout", None)
        print(f" [x] Recebido: aluno_id={aluno_id}, data={data_checkin}")
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
    channel.queue_declare(queue='churn', durable=True)
    channel.basic_consume(queue='churn', on_message_callback=callback)
    channel.start_consuming()

if __name__ == "__main__":
    start_consumer()