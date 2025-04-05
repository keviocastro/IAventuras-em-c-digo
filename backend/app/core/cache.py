import redis
import json
import logging
from typing import Any, Optional, Union, Dict, List
from app.core.config import settings

# Configurar logger
logger = logging.getLogger(__name__)

class DummyCache:
    """
    Implementação fake de cache para quando o Redis não estiver disponível.
    Implementa a mesma interface, mas não armazena nada.
    """
    def __init__(self):
        self._data = {}  # Armazenamento em memória simples, apenas para sessão atual
    
    def is_available(self) -> bool:
        return True  # Sempre disponível, pois é local
    
    def get(self, key: str) -> Any:
        # Retorna o valor se existir e não tiver expirado
        if key in self._data:
            return self._data[key]
        return None
    
    def set(self, key: str, value: Any, expire: int = None) -> bool:
        # Armazena o valor na memória
        self._data[key] = value
        return True
    
    def delete(self, key: str) -> bool:
        # Remove a chave se existir
        if key in self._data:
            del self._data[key]
            return True
        return False
    
    def clear_pattern(self, pattern: str) -> int:
        # Simula limpeza por padrão (simplificado)
        count = 0
        for key in list(self._data.keys()):
            if pattern.replace("*", "") in key:
                del self._data[key]
                count += 1
        return count

class RedisCache:
    """
    Cliente para interagir com o Redis como cache.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisCache, cls).__new__(cls)
            try:
                # Tentar conectar ao Redis com timeout curto
                cls._instance.client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=int(settings.REDIS_PORT),
                    password=settings.REDIS_PASSWORD,
                    db=settings.REDIS_DB,
                    decode_responses=True,  # Para decodificar strings automaticamente
                    socket_timeout=2,       # Timeout curto para não travar a app
                    socket_connect_timeout=2
                )
                # Testar conexão
                cls._instance.client.ping()
                logger.info("Conexão com Redis estabelecida com sucesso")
                cls._instance.use_dummy = False
            except Exception as e:
                logger.error(f"Erro ao conectar ao Redis: {e}")
                cls._instance.client = None
                cls._instance.dummy_cache = DummyCache()  # Usar cache fake
                cls._instance.use_dummy = True
                logger.warning("Usando cache local em memória como fallback. Algumas operações serão mais lentas e o cache será perdido ao reiniciar.")
        return cls._instance
    
    def is_available(self) -> bool:
        """Verifica se o cache está disponível"""
        if self.use_dummy:
            return self.dummy_cache.is_available()
            
        if not self.client:
            return False
        try:
            return self.client.ping()
        except:
            # Se falhar, mudar para modo fallback
            self.use_dummy = True
            self.dummy_cache = DummyCache()
            return True
    
    def get(self, key: str) -> Any:
        """
        Obtém um valor do cache.
        """
        if self.use_dummy:
            return self.dummy_cache.get(key)
            
        if not self.is_available():
            return None
        
        try:
            value = self.client.get(key)
            if value:
                try:
                    # Tentar decodificar como JSON
                    return json.loads(value)
                except:
                    # Se não for JSON, retornar como string
                    return value
            return None
        except Exception as e:
            logger.error(f"Erro ao obter do cache: {e}")
            return None
    
    def set(self, key: str, value: Any, expire: int = None) -> bool:
        """
        Define um valor no cache.
        
        Args:
            key: Chave para o valor
            value: Valor a ser armazenado (string, dict, list)
            expire: Tempo de expiração em segundos
        """
        if self.use_dummy:
            return self.dummy_cache.set(key, value, expire)
            
        if not self.is_available():
            return False
        
        try:
            # Converter para JSON se for um objeto
            if isinstance(value, (dict, list, tuple, bool, int, float)):
                value = json.dumps(value)
            
            # Definir no cache
            if expire:
                return self.client.setex(key, expire, value)
            else:
                return self.client.set(key, value)
        except Exception as e:
            logger.error(f"Erro ao definir no cache: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Remove um valor do cache.
        """
        if self.use_dummy:
            return self.dummy_cache.delete(key)
            
        if not self.is_available():
            return False
        
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Erro ao excluir do cache: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """
        Remove todos os valores que correspondem a um padrão.
        """
        if self.use_dummy:
            return self.dummy_cache.clear_pattern(pattern)
            
        if not self.is_available():
            return 0
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Erro ao limpar cache por padrão: {e}")
            return 0

# Instância global para ser usada por outros módulos
cache = RedisCache()

def get_cache() -> RedisCache:
    """
    Retorna a instância do cliente de cache.
    """
    return cache 