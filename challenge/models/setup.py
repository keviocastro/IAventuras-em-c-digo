import os
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv


def setup_database():
    """
    Executa o script setup.sql para criar as tabelas e inserir dados iniciais no banco de dados.
    """
    print("Iniciando configuração do banco de dados...")

    # Carrega variáveis de ambiente do arquivo .env
    load_dotenv()

    # Obtém a senha do ambiente ou usa um valor padrão para desenvolvimento local
    PASSWORD = os.getenv("DB_PASSWORD", "")

    # Configuração de conexão
    SQLALCHEMY_DATABASE_URL = (
        f"postgresql://postgres:{PASSWORD}@localhost:5432/postgres"
    )

    try:
        # Cria o engine de conexão
        engine = create_engine(SQLALCHEMY_DATABASE_URL)

        # Caminho para o arquivo setup.sql
        sql_file_path = Path(__file__).parent / "setup.sql"

        # Lê o conteúdo do arquivo SQL
        with open(sql_file_path, "r") as sql_file:
            sql_script = sql_file.read()

        # Executa o script SQL
        with engine.connect() as connection:
            sql_commands = sql_script.split(";")

            for command in sql_commands:
                if command.strip():
                    connection.execute(text(command))

            connection.commit()

        print("Banco de dados configurado com sucesso!")
        return True

    except Exception as e:
        print(f"Erro ao configurar banco de dados: {e}")
        return False


if __name__ == "__main__":
    setup_database()
