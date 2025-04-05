import pika
import json
import logging
import time
import os
from typing import Dict, Any, Callable, Optional
from app.core.config import settings

# Configurar logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Definir nomes das filas
CHECKIN_QUEUE = "checkin_queue"
REPORT_QUEUE = "daily_report_queue"
MODEL_UPDATE_QUEUE = "model_update_queue"
CHURN_PROB_QUEUE = "churn_probabilities_queue"

class RabbitMQClient:
    """
    Cliente para interagir com o RabbitMQ.
    """
    def __init__(self):
        self.connection = None
        self.channel = None
        self._connected = False
        self._connect()
    
    def _connect(self):
        """
        Estabelece conexão com o servidor RabbitMQ.
        """
        try:
            # Criar credenciais
            credentials = pika.PlainCredentials(
                settings.RABBITMQ_USER, 
                settings.RABBITMQ_PASSWORD
            )
            
            # Parâmetros de conexão com timeouts mais curtos e retry
            parameters = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=int(settings.RABBITMQ_PORT),
                credentials=credentials,
                heartbeat=60,  # Reduzir heartbeat para detectar problemas mais rápido
                blocked_connection_timeout=30,
                connection_attempts=2,  # Tentar reconectar
                retry_delay=1,  # Atrasar 1 segundo entre tentativas
                socket_timeout=5
            )
            
            # Estabelecer conexão
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declarar filas
            self.channel.queue_declare(queue=CHECKIN_QUEUE, durable=True)
            self.channel.queue_declare(queue=REPORT_QUEUE, durable=True)
            self.channel.queue_declare(queue=MODEL_UPDATE_QUEUE, durable=True)
            self.channel.queue_declare(queue=CHURN_PROB_QUEUE, durable=True)
            
            self._connected = True
            logger.info("Conexão estabelecida com o RabbitMQ")
        
        except Exception as e:
            self._connected = False
            self.connection = None
            self.channel = None
            logger.error(f"Erro ao conectar ao RabbitMQ: {e}")
            raise
    
    def is_connected(self) -> bool:
        """
        Verifica se a conexão com o RabbitMQ está ativa.
        """
        return (self.connection is not None and 
                self.connection.is_open and 
                self.channel is not None and 
                self.channel.is_open)
    
    def close(self):
        """
        Fecha a conexão com o RabbitMQ.
        """
        # Verificar se a conexão e o canal ainda estão abertos para evitar erros
        try:
            if self.channel and self.channel.is_open:
                self.channel.close()
                
            if self.connection and self.connection.is_open:
                self.connection.close()
                
            logger.info("Conexão com RabbitMQ fechada")
        except Exception as e:
            logger.warning(f"Erro ao fechar conexão RabbitMQ (ignorando): {e}")
        finally:
            # Garantir que as referências são limpas
            self.connection = None
            self.channel = None
            self._connected = False
    
    def _ensure_connection(self):
        """
        Garante que há uma conexão ativa antes de executar operações.
        """
        if not self.is_connected():
            try:
                self._connect()
            except Exception as e:
                logger.error(f"Falha ao reconectar com RabbitMQ: {e}")
                raise
    
    def publish_message(self, queue_name: str, message: Dict[str, Any]) -> bool:
        """
        Publica uma mensagem em uma fila específica.
        
        Returns:
            bool: True se a mensagem foi publicada com sucesso, False caso contrário
        """
        try:
            self._ensure_connection()
            
            self.channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistente
                    content_type='application/json'
                )
            )
            logger.info(f"Mensagem publicada na fila {queue_name}")
            return True
        except Exception as e:
            logger.error(f"Erro ao publicar mensagem: {e}")
            try:
                # Tentar reconectar e republicar uma vez
                self.close()
                self._connect()
                
                self.channel.basic_publish(
                    exchange='',
                    routing_key=queue_name,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type='application/json'
                    )
                )
                logger.info(f"Mensagem republicada na fila {queue_name} após reconexão")
                return True
            except Exception as retry_error:
                logger.error(f"Falha ao publicar mensagem após tentativa de reconexão: {retry_error}")
                return False
    
    def consume_messages(self, queue_name: str, callback: Callable):
        """
        Consome mensagens de uma fila específica.
        """
        try:
            self._ensure_connection()
            
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=False  # Não confirmar automaticamente
            )
            logger.info(f"Consumindo mensagens da fila {queue_name}")
            self.channel.start_consuming()
        except Exception as e:
            logger.error(f"Erro ao consumir mensagens: {e}")
            self.close()
            # Dormir um pouco antes de tentar reconectar para evitar loop infinito em caso de problemas
            time.sleep(2)
            raise
            
    def publish_bulk_checkin(self, checkins) -> bool:
        """
        Publica uma lista de checkins para processamento em massa.
        """
        return self.publish_message(CHECKIN_QUEUE, {"checkins": checkins})
    
    def request_daily_report(self, date=None) -> bool:
        """
        Solicita a geração de um relatório diário de frequência.
        """
        return self.publish_message(REPORT_QUEUE, {"date": date})
    
    def request_model_update(self, message) -> bool:
        """
        Envia solicitação para atualizar o modelo de previsão de churn.
        """
        return self.publish_message(MODEL_UPDATE_QUEUE, message)
    
    def request_churn_probabilities(self, message) -> bool:
        """
        Envia solicitação para calcular as probabilidades de churn de todos os alunos.
        """
        try:
            logger.info(f"Tipo de dados recebido em request_churn_probabilities: {type(message)}")
            logger.info(f"Conteúdo da mensagem: {message}")
            logger.info(f"Fila de destino: {CHURN_PROB_QUEUE}")
            
            result = self.publish_message(CHURN_PROB_QUEUE, message)
            if result:
                logger.info(f"Mensagem enviada com sucesso para a fila {CHURN_PROB_QUEUE}")
            return result
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para {CHURN_PROB_QUEUE}: {e}")
            return False

# Instância global para ser usada por outros módulos
rabbitmq_client = None

def get_rabbitmq_client() -> Optional[RabbitMQClient]:
    """
    Retorna um cliente RabbitMQ, criando um novo se necessário.
    
    Returns:
        RabbitMQClient ou None se não for possível conectar
    """
    global rabbitmq_client
    
    # Se já existe uma instância, verificar se está conectada
    if rabbitmq_client:
        try:
            if not rabbitmq_client.is_connected():
                logger.info("Reconectando ao RabbitMQ...")
                rabbitmq_client.close()  # Fechar conexão antiga
                rabbitmq_client = RabbitMQClient()  # Criar nova
            return rabbitmq_client
        except Exception as e:
            logger.error(f"Erro ao verificar conexão existente com RabbitMQ: {e}")
            # Continuar e tentar criar uma nova instância
    
    # Criar uma nova instância
    try:
        rabbitmq_client = RabbitMQClient()
        return rabbitmq_client
    except Exception as e:
        logger.warning(f"Não foi possível conectar ao RabbitMQ: {e}")
        logger.warning("Filas não estão disponíveis. Alguns recursos podem não funcionar corretamente.")
        return None 