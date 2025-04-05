import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.queue.rabbitmq import (
    get_rabbitmq_client,
    CHECKIN_QUEUE,
    REPORT_QUEUE,
    MODEL_UPDATE_QUEUE,
    CHURN_PROB_QUEUE
)

# Configurar logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def enviar_checkins_em_massa(checkins: List[Dict[str, Any]]) -> bool:
    """
    Envia uma lista de checkins para processamento assíncrono.
    
    Args:
        checkins: Lista de dicionários contendo os dados de checkin
                 (aluno_id, data_entrada, data_saida)
    
    Returns:
        bool: True se a mensagem foi enviada com sucesso, False caso contrário
    """
    try:
        client = get_rabbitmq_client()
        
        # Estruturar mensagem
        mensagem = {
            "checkins": checkins,
            "timestamp": datetime.now().isoformat()
        }
        
        # Converter para JSON
        mensagem_json = json.dumps(mensagem)
        logger.info(f"Enviando mensagem para fila: {mensagem_json}")
        
        # Enviar para a fila
        client.publish_bulk_checkin(mensagem_json)
        logger.info(f"Enviados {len(checkins)} checkins para processamento assíncrono")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao enviar checkins para a fila: {e}")
        return False


def solicitar_relatorio_diario(data: Optional[str] = None) -> bool:
    """
    Solicita a geração de um relatório diário de frequência.
    
    Args:
        data: Data para o relatório no formato 'YYYY-MM-DD'. 
              Se None, será usado o dia atual.
    
    Returns:
        bool: True se a mensagem foi enviada com sucesso, False caso contrário
    """
    try:
        client = get_rabbitmq_client()
        
        # Se a data não foi especificada, usar a data atual
        if not data:
            data = datetime.now().strftime("%Y-%m-%d")
            
        # Estruturar mensagem - garantir que date seja uma string simples
        mensagem = {
            "date": data,  # Deve ser uma string YYYY-MM-DD
            "request_timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Enviando solicitação de relatório para data: {data}")
        
        # Enviar para a fila
        client.request_daily_report(mensagem)
        logger.info(f"Solicitação de relatório para {data} enviada")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao solicitar relatório: {e}")
        return False


def solicitar_atualizacao_modelo() -> bool:
    """
    Solicita a atualização do modelo de previsão de churn.
    
    Returns:
        bool: True se a mensagem foi enviada com sucesso, False caso contrário
    """
    try:
        client = get_rabbitmq_client()
            
        # Estruturar mensagem
        mensagem = {
            "request_timestamp": datetime.now().isoformat()
        }
        
        logger.info("Enviando solicitação de atualização do modelo")
        
        # Enviar para a fila
        client.request_model_update(mensagem)
        logger.info("Solicitação de atualização do modelo de churn enviada")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao solicitar atualização do modelo: {e}")
        return False


def solicitar_calculo_probabilidades_churn() -> bool:
    """
    Solicita o cálculo das probabilidades de churn para todos os alunos.
    
    Returns:
        bool: True se a mensagem foi enviada com sucesso, False caso contrário
    """
    try:
        client = get_rabbitmq_client()
            
        # Estruturar mensagem
        mensagem = {
            "request_timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Enviando solicitação de cálculo de probabilidades de churn")
        
        # Enviar para a fila
        client.request_churn_probabilities(mensagem)
        logger.info("Solicitação de cálculo de probabilidades de churn enviada")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao solicitar cálculo de probabilidades de churn: {e}")
        return False 