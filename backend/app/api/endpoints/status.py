from fastapi import APIRouter, HTTPException, status, Depends
import pika
import logging
from datetime import datetime
import psutil
import os
import platform
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from app.core.config import settings
from app.db.database import get_db
from app.core.cache import get_cache
from app.queue.rabbitmq import get_rabbitmq_client
from app.api.dependencies import get_current_admin_user, get_current_active_user
from app.models.usuario import Usuario

router = APIRouter(prefix="/status", tags=["status"])


def verificar_rabbitmq():
    """
    Verifica a conexão com o RabbitMQ e retorna seu status.
    """
    try:
        # Usar o cliente RabbitMQ já configurado
        client = get_rabbitmq_client()
        
        if client and client.is_connected():
            return {
                "status": "online",
                "message": "Conexão estabelecida com sucesso"
            }
        else:
            return {
                "status": "offline",
                "message": "Não foi possível estabelecer conexão com o RabbitMQ"
            }
    except Exception as e:
        logging.error(f"Erro ao conectar com RabbitMQ: {e}")
        return {
            "status": "offline",
            "message": f"Erro ao conectar: {str(e)}"
        }


@router.get("/")
def obter_status_sistema(current_user: Usuario = Depends(get_current_admin_user)):
    """
    Retorna o status do sistema, incluindo componentes como RabbitMQ.
    Requer autenticação de administrador.
    """
    # Verificar status do RabbitMQ
    rabbitmq_status = verificar_rabbitmq()
    
    # Verificar status do Redis
    try:
        redis_cache = get_cache()
        cache_status = "online" if redis_cache.is_available() else "offline"
        cache_tipo = "dummy" if hasattr(redis_cache, 'use_dummy') and redis_cache.use_dummy else "redis"
    except Exception as e:
        cache_status = "erro"
        cache_tipo = "desconhecido"
    
    # Verificar status do banco de dados
    try:
        db = next(get_db())
        db.execute(text("SELECT 1")).scalar()
        db_status = "online"
        db.close()
    except Exception as e:
        db_status = "offline"
    
    # Montar resposta
    resposta = {
        "timestamp": datetime.now().isoformat(),
        "api": {"status": "online"},
        "rabbitmq": rabbitmq_status,
        "cache": {
            "status": cache_status,
            "tipo": cache_tipo
        },
        "database": {
            "status": db_status
        },
        "componentes": [
            {
                "nome": "API REST",
                "status": "online"
            },
            {
                "nome": "RabbitMQ",
                "status": rabbitmq_status["status"]
            },
            {
                "nome": "Cache",
                "status": cache_status,
                "tipo": cache_tipo
            },
            {
                "nome": "Banco de Dados",
                "status": db_status
            }
        ]
    }
    
    return resposta 


@router.get("/health")
def health_check():
    """
    Verifica se a API está em execução.
    Este endpoint é público para facilitar o monitoramento.
    """
    return {
        "status": "online",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/db")
def database_status(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_admin_user)
):
    """
    Verifica o status da conexão com o banco de dados.
    Requer autenticação de administrador.
    """
    try:
        # Executar uma consulta simples para verificar a conexão
        result = db.execute(text("SELECT 1")).scalar()
        return {
            "status": "conectado" if result == 1 else "erro",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "erro",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/queue")
def queue_status(current_user: Usuario = Depends(get_current_admin_user)):
    """
    Verifica o status da conexão com o RabbitMQ.
    Requer autenticação de administrador.
    """
    try:
        rabbitmq = get_rabbitmq_client()
        if rabbitmq and rabbitmq.is_connected():
            return {
                "status": "conectado",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "desconectado",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "status": "erro",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/cache")
def cache_status(current_user: Usuario = Depends(get_current_admin_user)):
    """
    Verifica o status da conexão com o Redis Cache.
    Requer autenticação de administrador.
    """
    try:
        redis_cache = get_cache()
        is_dummy = hasattr(redis_cache, 'use_dummy') and redis_cache.use_dummy
        
        if redis_cache.is_available():
            # Testar operações básicas
            test_key = "test:health"
            test_value = "ok"
            
            # Definir valor
            set_ok = redis_cache.set(test_key, test_value, 60)
            
            # Obter valor
            get_value = redis_cache.get(test_key)
            
            # Limpar teste
            redis_cache.delete(test_key)
            
            return {
                "status": "conectado",
                "tipo": "dummy" if is_dummy else "redis",
                "operations_test": "ok" if set_ok and get_value == test_value else "falha",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "desconectado",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "status": "erro",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/system")
def system_info(current_user: Usuario = Depends(get_current_admin_user)):
    """
    Retorna informações sobre o sistema.
    Requer autenticação de administrador.
    """
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "os": platform.system(),
        "python_version": platform.python_version(),
        "timestamp": datetime.now().isoformat()
    } 