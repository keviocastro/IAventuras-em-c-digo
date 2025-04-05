"""
Script para inicializar o banco de dados e criar as tabelas.
Execute este script antes de iniciar a aplicação.
"""
import os
import sys
from pathlib import Path

# Adiciona o diretório raiz do projeto ao PYTHONPATH
root_dir = str(Path(__file__).parent.parent.absolute())
sys.path.insert(0, root_dir)

# Carrega variáveis de ambiente do arquivo .env na raiz
from dotenv import load_dotenv
load_dotenv(os.path.join(root_dir, '.env'))

print("Carregando configurações do arquivo .env na raiz do projeto...")

# Agora importa o engine e os modelos
from app.db.database import engine
from app.models.aluno import Base

print("Iniciando criação das tabelas no banco de dados...")
print(f"Tentando conectar ao banco em: {os.environ.get('DB_HOST')}:{os.environ.get('DB_PORT')}/{os.environ.get('DB_NAME')}")

# Criar todas as tabelas
Base.metadata.create_all(bind=engine)

print("Tabelas criadas com sucesso!") 