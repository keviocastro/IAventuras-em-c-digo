import pika
import json
import logging
import time
import sys
import os
import datetime
import pandas as pd
from pathlib import Path
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    recall_score,
    precision_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report
)

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from config.project_constants import EnvVars
from utils.db.crud import PostgreSQLDatabase

env = EnvVars()
db_password = env.get_var("DB_PASSWORD")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

RABBITMQ_HOST = "localhost"
MODEL_UPDATE_QUEUE = "model_update_queue"
MODEL_BASE_PATH = "src/models"
MODEL_FILENAME = "model.pkl"
MODEL_VERSION_PREFIX = "model_v"

db = PostgreSQLDatabase(
    user="juanml",
    dbname="churnml",
    password=db_password,
    host="localhost",
    port="5432"
)

def load_data_from_file(file_path):
    try:
        df = pd.read_csv(file_path)
        logging.info(f"Dados carregados do arquivo: {file_path} com {len(df)} registros")
        return df
    except Exception as e:
        logging.error(f"Erro ao carregar dados do arquivo {file_path}: {e}")
        return None

def generate_features_from_db():
    logging.info("Gerando features a partir do banco de dados...")
    
    if not db.connect_db():
        logging.error("Falha ao conectar ao banco de dados para gerar features")
        return None
    
    try:
        query = """
        WITH aluno_features AS (
            SELECT
                a.id_aluno,
                a.nome_aluno,
                p.nome_plano,
                MAX(ci.data_checkin) as ultimo_checkin,
                MIN(m.data_inicio) as data_inicio_matricula,
                COUNT(ci.id_checkin) as total_checkins,
                CASE 
                    WHEN MAX(m.data_fim) < CURRENT_DATE THEN 1
                    ELSE 0
                END as churn
            FROM alunos a
            LEFT JOIN matriculas m ON a.id_aluno = m.id_aluno
            LEFT JOIN planos p ON m.id_plano = p.id_plano
            LEFT JOIN checkins ci ON a.id_aluno = ci.id_aluno
            GROUP BY a.id_aluno, a.nome_aluno, p.nome_plano
        )
        SELECT
            af.*,
            EXTRACT(DAY FROM NOW() - ultimo_checkin) as dias_desde_ultimo_checkin,
            EXTRACT(DAY FROM ultimo_checkin - data_inicio_matricula) / 7.0 as semanas_ativas,
            (SELECT AVG(EXTRACT(EPOCH FROM co.data_checkout - ci.data_checkin)/60)
             FROM checkins ci
             JOIN checkouts co ON ci.id_aluno = co.id_aluno AND co.data_checkout > ci.data_checkin
             WHERE ci.id_aluno = af.id_aluno) as duracao_media_minutos
        FROM aluno_features af
        WHERE af.total_checkins > 0
        """
        
        db.cursor.execute(query)
        rows = db.cursor.fetchall()
        column_names = [desc[0] for desc in db.cursor.description]
        
        df = pd.DataFrame(rows, columns=column_names)
        
        df["frequencia_semanal"] = df["total_checkins"] / df["semanas_ativas"].clip(lower=1)
        df["tempo_desde_ultimo_checkin"] = df["dias_desde_ultimo_checkin"].fillna(30)
        df["duracao_media_visitas"] = df["duracao_media_minutos"].fillna(0)
        
        df["tipo_plano_Mensal"] = df["nome_plano"].str.lower().str.contains("mensal").fillna(False).astype(int)
        df["tipo_plano_Semestral"] = df["nome_plano"].str.lower().str.contains("semestral").fillna(False).astype(int)
        
        features_df = df[[
            "frequencia_semanal", 
            "tempo_desde_ultimo_checkin", 
            "duracao_media_visitas", 
            "tipo_plano_Mensal", 
            "tipo_plano_Semestral",
            "churn"
        ]]
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"data/features_{timestamp}.csv"
        features_df.to_csv(output_path, index=False)
        logging.info(f"Features geradas e salvas em {output_path} com {len(features_df)} registros")
        
        return features_df
    
    except Exception as e:
        logging.exception(f"Erro ao gerar features a partir do banco de dados: {e}")
        return None
    finally:
        db.close_db()

def train_model(data_df):
    logging.info("Iniciando treinamento do modelo...")
    
    try:
        X = data_df.drop(columns=['churn'])
        y = data_df['churn']
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        model = RandomForestClassifier(
            bootstrap=True,
            class_weight="balanced",
            max_depth=30,
            min_samples_leaf=2,
            min_samples_split=5,
            n_estimators=100,
            random_state=42
        )
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]
        
        acc = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        rocauc = roc_auc_score(y_test, y_proba)
        cm = confusion_matrix(y_test, y_pred)
        cr = classification_report(y_test, y_pred)
        
        logging.info(f"\nAccuracy: {acc:.4f}")
        logging.info(f"Precision: {precision:.4f}")
        logging.info(f"Recall: {recall:.4f}")
        logging.info(f"F1: {f1:.4f}")
        logging.info(f"ROC AUC: {rocauc:.4f}")
        logging.info(f"Confusion Matrix:\n{cm}")
        logging.info(f"Classification Report:\n{cr}")
        
        return model, {
            "accuracy": acc,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "roc_auc": rocauc,
            "features": list(X.columns),
            "training_size": len(X_train),
            "test_size": len(X_test),
            "timestamp": datetime.datetime.now().isoformat()
        }
    
    except Exception as e:
        logging.exception(f"Erro ao treinar o modelo: {e}")
        return None, None

def save_model(model, metadata):
    os.makedirs(MODEL_BASE_PATH, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    model_version = f"{MODEL_VERSION_PREFIX}{timestamp}"
    
    model_path = os.path.join(MODEL_BASE_PATH, f"{model_version}.pkl")
    
    try:
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        current_model_path = os.path.join(MODEL_BASE_PATH, MODEL_FILENAME)
        with open(current_model_path, 'wb') as f:
            pickle.dump(model, f)
        
        metadata_path = os.path.join(MODEL_BASE_PATH, f"{model_version}_metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=4)
            
        current_version_path = os.path.join(MODEL_BASE_PATH, "current_version.txt")
        with open(current_version_path, 'w') as f:
            f.write(model_version)
            
        logging.info(f"Modelo salvo com sucesso: {model_path}")
        logging.info(f"Metadados salvos: {metadata_path}")
        logging.info(f"Modelo definido como atual: {current_model_path}")
        
        return True
    
    except Exception as e:
        logging.exception(f"Erro ao salvar o modelo: {e}")
        return False

def process_model_update(channel, method, properties, body):
    logging.info(f"Recebida solicitação de atualização do modelo: {body}")
    
    try:
        message = json.loads(body.decode('utf-8'))
        data_path = message.get('data_path')
        force_update = message.get('force_update', False)
        
        if data_path and os.path.exists(data_path):
            df = load_data_from_file(data_path)
        else:
            df = generate_features_from_db()
        
        if df is not None and len(df) > 0:
            model, metadata = train_model(df)
            
            if model is not None:
                save_success = save_model(model, metadata)
                
                if save_success:
                    logging.info("Atualização do modelo completada com sucesso!")
                else:
                    logging.error("Falha ao salvar o modelo atualizado.")
            else:
                logging.error("Falha ao treinar o modelo.")
        else:
            logging.error("Não foi possível obter dados para treinar o modelo.")
        
        channel.basic_ack(delivery_tag=method.delivery_tag)
    
    except json.JSONDecodeError:
        logging.error(f"Erro ao decodificar JSON da mensagem: {body}")
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logging.exception(f"Erro inesperado ao processar atualização do modelo: {e}")
        channel.basic_ack(delivery_tag=method.delivery_tag)

def main():
    connection = None
    
    while True:
        try:
            logging.info(f"Tentando conectar ao RabbitMQ em {RABBITMQ_HOST} para o worker de atualização do modelo...")
            connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
            channel = connection.channel()
            
            channel.queue_declare(queue=MODEL_UPDATE_QUEUE, durable=True)
            logging.info(f"Conectado ao RabbitMQ. Aguardando solicitações de atualização do modelo...")
            
            channel.basic_qos(prefetch_count=1)
            
            channel.basic_consume(
                queue=MODEL_UPDATE_QUEUE,
                on_message_callback=process_model_update
            )
            
            channel.start_consuming()
            
        except pika.exceptions.AMQPConnectionError as conn_err: # https://pika.readthedocs.io/en/stable/modules/exceptions.html
            logging.error(f"Falha na conexão com RabbitMQ: {conn_err}. Tentando reconectar em 10 segundos...")
            if connection and not connection.is_closed:
                connection.close()
            time.sleep(10)
        except KeyboardInterrupt:
            logging.info("Worker de atualização do modelo interrompido pelo usuário.")
            if connection and not connection.is_closed:
                connection.close()
            break
        except Exception as general_err:
            logging.exception(f"Erro inesperado no worker: {general_err}. Reiniciando em 10 segundos...")
            if connection and not connection.is_closed:
                connection.close()
            time.sleep(10)

if __name__ == "__main__":
    main()