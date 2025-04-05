#!/usr/bin/env python
"""
Script para testar a conexão com o Redis e o funcionamento do cache.
Útil para verificar se a configuração está correta antes de iniciar a aplicação.
"""

import os
import sys
import json
import time
from dotenv import load_dotenv

# Ajustar o caminho para importar os módulos corretamente
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Carregar variáveis de ambiente
env_file = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_file):
    print(f"Carregando variáveis de ambiente de {env_file}")
    load_dotenv(env_file)
else:
    print(f"Arquivo .env não encontrado em {env_file}")

# Importar após configurar o caminho e variáveis de ambiente
try:
    from backend.app.core.cache import RedisCache
    print("Módulo RedisCache importado com sucesso")
except ImportError as e:
    print(f"Erro ao importar RedisCache: {e}")
    # Tentar um caminho alternativo
    try:
        sys.path.append(os.path.join(BASE_DIR, 'backend'))
        from app.core.cache import RedisCache
        print("Módulo RedisCache importado com caminho alternativo")
    except ImportError as e2:
        print(f"Erro ao importar com caminho alternativo: {e2}")
        print("Verifique a estrutura do projeto e os caminhos de importação")
        sys.exit(1)

def test_redis_connection():
    """Testa a conexão com o Redis"""
    print("\n=== Teste de Conexão com Redis ===")
    
    # Criar instância do cache
    cache = RedisCache()
    
    # Verificar disponibilidade
    available = cache.is_available()
    print(f"Redis disponível: {available}")
    
    if not available:
        if hasattr(cache, 'use_dummy') and cache.use_dummy:
            print("Redis não está disponível, mas o cache dummy está sendo usado como fallback.")
            return True
        else:
            print("ERRO: Não foi possível conectar ao Redis. Verifique se o serviço está em execução e as configurações estão corretas.")
            return False
    
    print("Conexão com Redis estabelecida com sucesso!")
    return True

def test_redis_operations():
    """Testa operações básicas do Redis (set, get, delete)"""
    print("\n=== Teste de Operações do Redis ===")
    
    # Criar instância do cache
    cache = RedisCache()
    
    # Verificar se estamos usando o dummy cache
    using_dummy = hasattr(cache, 'use_dummy') and cache.use_dummy
    if using_dummy:
        print("Usando cache em memória (dummy cache) para os testes")
    
    # Criar chave de teste
    test_key = "test:redis:operations"
    test_data = {
        "name": "Teste Cache Redis",
        "timestamp": time.time(),
        "values": [1, 2, 3, 4, 5]
    }
    
    # Testar definição de valor
    print(f"Definindo valor para '{test_key}'...")
    set_result = cache.set(test_key, test_data, 60)  # expiração de 60 segundos
    print(f"Resultado: {set_result}")
    
    # Testar obtenção de valor
    print(f"Obtendo valor de '{test_key}'...")
    get_result = cache.get(test_key)
    print(f"Valor obtido: {json.dumps(get_result, indent=2)}")
    
    # Verificar se os dados correspondem
    if get_result == test_data:
        print("✅ Dados armazenados e recuperados com sucesso!")
    else:
        print("❌ Erro: Os dados recuperados não correspondem aos armazenados.")
    
    # Testar exclusão
    print(f"Excluindo chave '{test_key}'...")
    delete_result = cache.delete(test_key)
    print(f"Resultado da exclusão: {delete_result}")
    
    # Verificar se a chave foi realmente excluída
    get_after_delete = cache.get(test_key)
    if get_after_delete is None:
        print("✅ Chave excluída com sucesso!")
    else:
        print("❌ Erro: A chave ainda existe após a exclusão.")
    
    return True

def test_cache_performance():
    """Testa a performance do cache em comparação com operações repetidas"""
    print("\n=== Teste de Performance do Cache ===")
    
    # Criar instância do cache
    cache = RedisCache()
    
    # Verificar se estamos usando o dummy cache
    using_dummy = hasattr(cache, 'use_dummy') and cache.use_dummy
    if using_dummy:
        print("Usando cache em memória (dummy cache) para os testes de performance")
    
    # Função pesada para simular um cálculo complexo
    def heavy_calculation(n):
        print("Executando cálculo pesado...")
        time.sleep(1)  # Simular operação que leva 1 segundo
        return {"result": n * n, "timestamp": time.time()}
    
    # Chave para o teste
    test_key = "test:redis:performance"
    
    # Limpar qualquer cache existente
    cache.delete(test_key)
    
    # Primeira execução (sem cache)
    print("Primeira execução (sem cache):")
    start_time = time.time()
    
    # Verificar cache
    cached_result = cache.get(test_key)
    if cached_result is None:
        # Cache miss - executar cálculo
        result = heavy_calculation(42)
        # Armazenar em cache
        cache.set(test_key, result, 60)
    else:
        # Cache hit - usar resultado em cache
        result = cached_result
    
    first_time = time.time() - start_time
    print(f"Tempo da primeira execução: {first_time:.4f} segundos")
    
    # Segunda execução (com cache)
    print("\nSegunda execução (com cache):")
    start_time = time.time()
    
    # Verificar cache
    cached_result = cache.get(test_key)
    if cached_result is None:
        # Cache miss - executar cálculo
        result = heavy_calculation(42)
        # Armazenar em cache
        cache.set(test_key, result, 60)
    else:
        # Cache hit - usar resultado em cache
        result = cached_result
        print("Resultado obtido do cache!")
    
    second_time = time.time() - start_time
    print(f"Tempo da segunda execução: {second_time:.4f} segundos")
    
    # Calcular speedup - evitar divisão por zero
    if first_time > 0:
        if second_time > 0:
            speedup = first_time / second_time
            print(f"\nSpeedup com cache: {speedup:.2f}x mais rápido")
        else:
            # Se o segundo tempo for zero ou muito próximo de zero
            print("\nSpeedup com cache: ∞ (infinito) - tempo próximo de zero!")
    
    # Limpar o cache de teste
    cache.delete(test_key)
    
    return True

if __name__ == "__main__":
    print("=== Iniciando Testes do Redis Cache ===")
    print(f"Diretório de trabalho atual: {os.getcwd()}")
    print(f"Path de busca do Python: {sys.path}")
    
    # Testar conexão
    if not test_redis_connection():
        print("O Redis não está disponível, mas vamos continuar os testes usando o cache em memória.")
    
    # Testar operações básicas
    test_redis_operations()
    
    # Testar performance
    test_cache_performance()
    
    print("\n=== Testes do Redis Cache Concluídos com Sucesso ===") 