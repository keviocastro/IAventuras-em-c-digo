#!/usr/bin/env python
"""
Script para criar um usuário administrador inicial.
"""
import sys
import os
from dotenv import load_dotenv

# Adicionar diretório raiz ao caminho
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, "backend"))  # Adiciona o diretório backend ao path

# Carregar variáveis de ambiente
env_file = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_file):
    print(f"Carregando variáveis de ambiente de {env_file}")
    load_dotenv(env_file)
else:
    print(f"Arquivo .env não encontrado em {env_file}")

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.usuario_service import UsuarioService

def create_admin_user(username, email, password):
    """Cria um usuário administrador"""
    try:
        db = SessionLocal()
        
        try:
            # Usar serviço para criar usuário admin
            service = UsuarioService(db)
            user = service.create_admin_user(username, email, password)
            
            print(f"Usuário administrador '{user.username}' criado com sucesso!")
            return True
        except Exception as e:
            print(f"Erro ao criar usuário administrador: {e}")
            return False
        finally:
            db.close()
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Criar usuário administrador')
    parser.add_argument('--username', default="admin", help='Nome de usuário do administrador (padrão: admin)')
    parser.add_argument('--email', default="admin@academia.com", help='Email do administrador (padrão: admin@academia.com)')
    parser.add_argument('--password', default="admin", help='Senha do administrador (padrão: admin)')
    
    args = parser.parse_args()
    
    print(f"Criando usuário administrador '{args.username}'...")
    create_admin_user(args.username, args.email, args.password) 