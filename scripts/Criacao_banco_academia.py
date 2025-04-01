import psycopg2
import json
import os
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Caminho absoluto até o banco.json na pasta anterior
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "banco.json")

# Carregar configurações do banco
with open(config_path, "r") as f:
    db_config = json.load(f)

# Separar o nome do banco (útil se quiser criar o banco depois)
nome_banco = db_config["dbname"]

# Você pode acessar outras variáveis individualmente, se quiser
host = db_config["host"]
port = db_config["port"]
user = db_config["user"]
password = db_config["password"]

# CONECTA AO POSTGRES (para criar o banco)
con = psycopg2.connect(
    dbname="postgres",
    user=user,
    password=password,
    host=host,
    port=port
)
con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = con.cursor()

# CRIA O BANCO DE DADOS
try:
    cur.execute(f"CREATE DATABASE {nome_banco};")
    print(f"Banco de dados '{nome_banco}' criado com sucesso.")
except psycopg2.errors.DuplicateDatabase:
    print(f"O banco de dados '{nome_banco}' já existe.")

cur.close()
con.close()

# CONECTA AO BANCO 'academia' PARA CRIAR AS TABELAS
con = psycopg2.connect(
    dbname=nome_banco,
    user=user,
    password=password,
    host=host,
    port=port
)
cur = con.cursor()

# CRIA TABELAS
cur.execute("""
    CREATE TABLE IF NOT EXISTS planos (
        id SERIAL PRIMARY KEY,
        nome VARCHAR(50) NOT NULL,
        preco NUMERIC(10, 2) NOT NULL
    );
""")

cur.execute("""
    CREATE TABLE IF NOT EXISTS alunos (
        id SERIAL PRIMARY KEY,
        nome VARCHAR(100) NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        data_nascimento DATE NOT NULL,
        plano_id INTEGER REFERENCES planos(id)
    );
""")

cur.execute("""
    CREATE TABLE IF NOT EXISTS checkins (
        id SERIAL PRIMARY KEY,
        aluno_id INTEGER REFERENCES alunos(id),
        data_checkin TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data_checkout TIMESTAMP,
        duracao INTERVAL GENERATED ALWAYS AS (data_checkout - data_checkin) STORED
    );
""")

con.commit()
cur.close()
con.close()

print("Tabelas criadas com sucesso no banco de dados 'academia'.")
