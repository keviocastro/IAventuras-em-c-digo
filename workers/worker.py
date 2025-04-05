import sys
import os
import json
import time
import datetime
import pika
import logging
from typing import Dict, Any
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pickle

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Adicionar o diretório raiz ao PATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.core.config import settings
from backend.app.db.database import SessionLocal, engine
from backend.app.models.aluno import Aluno, Checkin


class Worker:
    def __init__(self):
        """
        Inicializa o worker para processamento assíncrono.
        """
        self.connection = None
        self.channel = None
        self.db = SessionLocal()
    
    def conectar_rabbitmq(self):
        """
        Estabelece conexão com o RabbitMQ.
        """
        try:
            # Parâmetros de conexão
            credentials = pika.PlainCredentials(
                settings.RABBITMQ_USER, 
                settings.RABBITMQ_PASSWORD
            )
            parameters = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=int(settings.RABBITMQ_PORT),
                credentials=credentials
            )
            
            # Estabelecer conexão
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declarar filas
            self.channel.queue_declare(queue='checkin_queue', durable=True)
            self.channel.queue_declare(queue='daily_report_queue', durable=True)
            self.channel.queue_declare(queue='model_update_queue', durable=True)
            self.channel.queue_declare(queue='churn_probabilities_queue', durable=True)
            
            logger.info("Conexão com RabbitMQ estabelecida com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar com RabbitMQ: {e}")
            return False
    
    def processar_checkins_massa(self, dados: Dict[str, Any]):
        """
        Processa múltiplos checkins em massa.
        """
        logger.info(f"Processando {len(dados['checkins'])} checkins em massa")
        
        try:
            checkins_criados = 0
            
            for checkin_data in dados['checkins']:
                aluno_id = checkin_data.get('aluno_id')
                data_entrada_str = checkin_data.get('data_entrada')
                data_saida_str = checkin_data.get('data_saida')
                
                # Converter strings para datetime
                data_entrada = datetime.datetime.fromisoformat(data_entrada_str)
                data_saida = None
                if data_saida_str:
                    data_saida = datetime.datetime.fromisoformat(data_saida_str)
                    duracao = (data_saida - data_entrada).total_seconds() / 60
                else:
                    duracao = None
                
                # Criar objeto Checkin
                checkin = Checkin(
                    aluno_id=aluno_id,
                    data_entrada=data_entrada,
                    data_saida=data_saida,
                    duracao_minutos=duracao
                )
                
                # Adicionar ao banco de dados
                self.db.add(checkin)
                checkins_criados += 1
            
            # Commit das alterações
            self.db.commit()
            logger.info(f"{checkins_criados} checkins processados com sucesso")
            
            return {
                "status": "success",
                "message": f"{checkins_criados} checkins processados com sucesso"
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao processar checkins em massa: {e}")
            return {
                "status": "error",
                "message": f"Erro ao processar checkins: {str(e)}"
            }
    
    def gerar_relatorio_diario(self, dados: Dict[str, Any]):
        """
        Gera relatório diário de frequência.
        """
        data_relatorio = dados.get('data', datetime.datetime.now().strftime('%Y-%m-%d'))
        logger.info(f"Gerando relatório diário para {data_relatorio}")
        
        try:
            # Consulta SQL para obter dados do dia
            query = text("""
                SELECT 
                    a.id AS aluno_id,
                    a.nome AS nome_aluno,
                    p.nome AS plano,
                    COUNT(c.id) AS total_checkins,
                    MIN(c.data_entrada) AS primeira_entrada,
                    MAX(c.data_saida) AS ultima_saida,
                    AVG(c.duracao_minutos) AS duracao_media
                FROM 
                    alunos a
                LEFT JOIN 
                    checkins c ON a.id = c.aluno_id AND DATE(c.data_entrada) = :data
                LEFT JOIN
                    planos p ON a.plano_id = p.id
                GROUP BY 
                    a.id, a.nome, p.nome
                ORDER BY 
                    total_checkins DESC, nome_aluno
            """)
            
            # Executar consulta
            result = self.db.execute(query, {"data": data_relatorio})
            rows = result.fetchall()
            
            # Construir relatório
            relatorio = {
                "data": data_relatorio,
                "total_alunos": len(rows),
                "total_visitas": sum(row.total_checkins for row in rows if row.total_checkins),
                "detalhes": [
                    {
                        "aluno_id": row.aluno_id,
                        "nome": row.nome_aluno,
                        "plano": row.plano,
                        "checkins": row.total_checkins if row.total_checkins else 0,
                        "primeira_entrada": row.primeira_entrada.strftime('%H:%M:%S') if row.primeira_entrada else None,
                        "ultima_saida": row.ultima_saida.strftime('%H:%M:%S') if row.ultima_saida else None,
                        "duracao_media": round(row.duracao_media, 1) if row.duracao_media else None
                    }
                    for row in rows
                ]
            }
            
            # Salvar relatório em arquivo
            relatorio_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "relatorios")
            os.makedirs(relatorio_dir, exist_ok=True)
            
            relatorio_path = os.path.join(relatorio_dir, f"relatorio_{data_relatorio}.json")
            with open(relatorio_path, 'w') as f:
                json.dump(relatorio, f, indent=4)
            
            logger.info(f"Relatório diário salvo em {relatorio_path}")
            
            return {
                "status": "success",
                "message": f"Relatório diário gerado com sucesso para {data_relatorio}",
                "path": relatorio_path
            }
        except Exception as e:
            logger.error(f"Erro ao gerar relatório diário: {e}")
            return {
                "status": "error",
                "message": f"Erro ao gerar relatório: {str(e)}"
            }
    
    def atualizar_modelo_churn(self, dados: Dict[str, Any]):
        """
        Atualiza o modelo de previsão de churn.
        """
        logger.info("Atualizando modelo de previsão de churn")
        
        try:
            # Obter dados para treinamento
            query = text("""
                SELECT
                    a.id AS aluno_id,
                    a.ativo,
                    COUNT(c.id) AS total_checkins,
                    MAX(c.data_entrada) AS ultima_visita,
                    AVG(c.duracao_minutos) AS duracao_media,
                    EXTRACT(DAY FROM NOW() - MAX(c.data_entrada)) AS dias_desde_ultima_visita,
                    COUNT(c.id) / GREATEST(1, EXTRACT(DAY FROM NOW() - MIN(c.data_entrada)) / 7) AS media_visitas_semanais,
                    p.id AS plano_id
                FROM
                    alunos a
                LEFT JOIN
                    checkins c ON a.id = c.aluno_id
                LEFT JOIN
                    planos p ON a.plano_id = p.id
                GROUP BY
                    a.id, a.ativo, p.id
            """)
            
            # Executar consulta
            result = self.db.execute(query)
            rows = result.fetchall()
            
            # Criar DataFrame
            df = pd.DataFrame([dict(row) for row in rows])
            
            # Preprocessamento
            df['dias_desde_ultima_visita'].fillna(365, inplace=True)  # Valor alto para alunos sem visitas
            df['duracao_media'].fillna(0, inplace=True)
            df['media_visitas_semanais'].fillna(0, inplace=True)
            
            # Definir variáveis
            X = df[['total_checkins', 'dias_desde_ultima_visita', 'duracao_media', 'media_visitas_semanais', 'plano_id']]
            y = df['ativo'] == 0  # ativo=0 significa que o aluno já saiu (churn)
            
            # Treinar modelo (Regressão Logística simples)
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import StandardScaler
            
            # Normalizar os dados
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Treinar modelo
            modelo = LogisticRegression(random_state=42)
            modelo.fit(X_scaled, y)
            
            # Salvar modelo
            model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
            os.makedirs(model_dir, exist_ok=True)
            
            model_path = os.path.join(model_dir, "modelo_churn.pkl")
            with open(model_path, 'wb') as f:
                pickle.dump({
                    'modelo': modelo,
                    'scaler': scaler,
                    'features': X.columns.tolist(),
                    'data_treinamento': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }, f)
            
            logger.info(f"Modelo de previsão de churn atualizado e salvo em {model_path}")
            
            return {
                "status": "success",
                "message": "Modelo de previsão de churn atualizado com sucesso",
                "path": model_path
            }
        except Exception as e:
            logger.error(f"Erro ao atualizar modelo de previsão de churn: {e}")
            return {
                "status": "error",
                "message": f"Erro ao atualizar modelo: {str(e)}"
            }
    
    def callback_checkins_massa(self, ch, method, properties, body):
        """
        Callback para processar mensagens da fila de checkins em massa.
        """
        try:
            dados = json.loads(body)
            logger.info(f"Recebida mensagem da fila 'checkin_queue': {len(dados.get('checkins', []))} checkins")
            resultado = self.processar_checkins_massa(dados)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"Erro ao processar mensagem de checkins em massa: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def callback_relatorios_diarios(self, ch, method, properties, body):
        """
        Callback para processar mensagens da fila de relatórios diários.
        """
        try:
            dados = json.loads(body)
            logger.info(f"Recebida mensagem da fila 'daily_report_queue' para data: {dados.get('data', 'hoje')}")
            resultado = self.gerar_relatorio_diario(dados)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"Erro ao processar mensagem de relatório diário: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def callback_atualizar_modelo(self, ch, method, properties, body):
        """
        Callback para processar mensagens da fila de atualização de modelo.
        """
        try:
            dados = json.loads(body)
            logger.info("Recebida mensagem da fila 'model_update_queue'")
            resultado = self.atualizar_modelo_churn(dados)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"Erro ao processar mensagem de atualização de modelo: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def calcular_probabilidades_churn(self, dados: Dict[str, Any]):
        """
        Calcula as probabilidades de churn para todos os alunos ativos.
        """
        logger.info("Calculando probabilidades de churn para todos os alunos ativos")
        
        try:
            # Verificar se o modelo existe
            model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
            model_path = os.path.join(model_dir, "modelo_churn.pkl")
            
            if not os.path.exists(model_path):
                logger.error(f"Modelo não encontrado em {model_path}. Execute primeiro a atualização do modelo.")
                return {
                    "status": "error",
                    "message": "Modelo de previsão de churn não encontrado. Execute primeiro a atualização do modelo."
                }
            
            # Carregar o modelo
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
                
            modelo = model_data['modelo']
            scaler = model_data['scaler']
            features = model_data['features']
            
            # Obter dados de todos os alunos ativos
            query = text("""
                SELECT
                    a.id AS aluno_id,
                    COUNT(c.id) AS total_checkins,
                    MAX(c.data_entrada) AS ultima_visita,
                    AVG(c.duracao_minutos) AS duracao_media,
                    EXTRACT(DAY FROM NOW() - MAX(c.data_entrada)) AS dias_desde_ultima_visita,
                    COUNT(c.id) / GREATEST(1, EXTRACT(DAY FROM NOW() - MIN(c.data_entrada)) / 7) AS media_visitas_semanais,
                    p.id AS plano_id
                FROM
                    alunos a
                LEFT JOIN
                    checkins c ON a.id = c.aluno_id
                LEFT JOIN
                    planos p ON a.plano_id = p.id
                WHERE
                    a.ativo = 1
                GROUP BY
                    a.id, p.id
            """)
            
            # Executar consulta
            result = self.db.execute(query)
            rows = result.fetchall()
            
            # Criar DataFrame
            df = pd.DataFrame([dict(row) for row in rows])
            
            if df.empty:
                logger.warning("Nenhum aluno ativo encontrado para cálculo de probabilidades")
                return {
                    "status": "warning",
                    "message": "Nenhum aluno ativo encontrado para cálculo de probabilidades"
                }
            
            # Preprocessamento
            df['dias_desde_ultima_visita'].fillna(365, inplace=True)  # Valor alto para alunos sem visitas
            df['duracao_media'].fillna(0, inplace=True)
            df['media_visitas_semanais'].fillna(0, inplace=True)
            
            # Garantir que todas as features estão presentes
            for feature in features:
                if feature not in df.columns:
                    df[feature] = 0
            
            # Selecionar apenas as features usadas pelo modelo
            X = df[features]
            
            # Normalizar os dados
            X_scaled = scaler.transform(X)
            
            # Prever probabilidades
            probs = modelo.predict_proba(X_scaled)[:, 1]  # Probabilidade da classe 1 (churn)
            
            # Adicionar probabilidades ao DataFrame
            df['probabilidade_churn'] = probs
            
            # Atualizar no banco de dados
            total_atualizados = 0
            for _, row in df.iterrows():
                aluno_id = row['aluno_id']
                prob_churn = float(row['probabilidade_churn'])
                dias = float(row['dias_desde_ultima_visita']) if not pd.isna(row['dias_desde_ultima_visita']) else None
                
                # Verificar se já existe um registro para este aluno
                check_query = text("SELECT id FROM churn_probabilidades WHERE aluno_id = :aluno_id")
                result = self.db.execute(check_query, {"aluno_id": aluno_id}).fetchone()
                
                if result:
                    # Atualizar registro existente
                    update_query = text("""
                        UPDATE churn_probabilidades 
                        SET probabilidade = :prob, 
                            dias_desde_ultima_visita = :dias,
                            data_atualizacao = NOW()
                        WHERE aluno_id = :aluno_id
                    """)
                    self.db.execute(update_query, {
                        "prob": prob_churn,
                        "dias": dias,
                        "aluno_id": aluno_id
                    })
                else:
                    # Inserir novo registro
                    insert_query = text("""
                        INSERT INTO churn_probabilidades 
                        (aluno_id, probabilidade, dias_desde_ultima_visita, data_atualizacao)
                        VALUES (:aluno_id, :prob, :dias, NOW())
                    """)
                    self.db.execute(insert_query, {
                        "aluno_id": aluno_id,
                        "prob": prob_churn,
                        "dias": dias
                    })
                
                total_atualizados += 1
            
            # Commit das alterações
            self.db.commit()
            
            logger.info(f"Probabilidades de churn calculadas para {total_atualizados} alunos")
            
            return {
                "status": "success",
                "message": f"Probabilidades de churn calculadas para {total_atualizados} alunos",
                "total_atualizados": total_atualizados
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao calcular probabilidades de churn: {e}")
            return {
                "status": "error",
                "message": f"Erro ao calcular probabilidades de churn: {str(e)}"
            }
    
    def callback_calcular_probabilidades(self, ch, method, properties, body):
        """
        Callback para processar mensagens da fila de cálculo de probabilidades de churn.
        """
        try:
            dados = json.loads(body)
            logger.info("Recebida mensagem da fila 'churn_probabilities_queue'")
            resultado = self.calcular_probabilidades_churn(dados)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"Erro ao processar mensagem de cálculo de probabilidades: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def iniciar(self):
        """
        Inicia o worker para consumir mensagens das filas.
        """
        if not self.conectar_rabbitmq():
            logger.error("Não foi possível conectar ao RabbitMQ. Encerrando worker.")
            return
        
        # Configurar consumidores
        self.channel.basic_consume(queue='checkin_queue', on_message_callback=self.callback_checkins_massa)
        self.channel.basic_consume(queue='daily_report_queue', on_message_callback=self.callback_relatorios_diarios)
        self.channel.basic_consume(queue='model_update_queue', on_message_callback=self.callback_atualizar_modelo)
        self.channel.basic_consume(queue='churn_probabilities_queue', on_message_callback=self.callback_calcular_probabilidades)
        
        logger.info("Worker iniciado e aguardando mensagens. Pressione CTRL+C para sair.")
        
        try:
            # Iniciar consumo de mensagens
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Worker interrompido pelo usuário")
            self.channel.stop_consuming()
        finally:
            if self.connection and self.connection.is_open:
                self.connection.close()
            self.db.close()


if __name__ == "__main__":
    worker = Worker()
    worker.iniciar() 