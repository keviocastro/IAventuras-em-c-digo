import psycopg2
from faker import Faker
import random
import json
from datetime import datetime, timedelta
import os

# Caminho absoluto até o banco.json na pasta anterior
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "banco.json")

# Configurações do banco
with open(config_path, "r") as f:
    db_config = json.load(f)

# Conexão
con = psycopg2.connect(**db_config)
cur = con.cursor()

fake = Faker('pt_BR')

# -------------------------
# 1. Inserir planos
# -------------------------
planos = [
    ("Mensal", 99.90),
    ("Trimestral", 249.90),
    ("Anual", 899.90)
]

cur.executemany("""
    INSERT INTO planos (nome, preco) VALUES (%s, %s)
    ON CONFLICT DO NOTHING
""", planos)
con.commit()

# Pegar IDs dos planos
cur.execute("SELECT id FROM planos")
plano_ids = [row[0] for row in cur.fetchall()]

# -------------------------
# 2. Inserir alunos
# -------------------------
for _ in range(100):
    nome = fake.name()
    email = fake.email()
    data_nascimento = fake.date_of_birth(minimum_age=18, maximum_age=60)
    plano_id = random.choice(plano_ids)

    cur.execute("""
        INSERT INTO alunos (nome, email, data_nascimento, plano_id)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (email) DO NOTHING
    """, (nome, email, data_nascimento, plano_id))

con.commit()

# -------------------------
# 3. Inserir check-ins aleatórios (com entrada e saída)
# -------------------------
cur.execute("SELECT id FROM alunos")
aluno_ids = [row[0] for row in cur.fetchall()]

for aluno_id in aluno_ids:
    for _ in range(random.randint(3, 10)):  # de 3 a 10 check-ins por aluno
        dias_atras = random.randint(0, 30)
        hora_random = random.randint(6, 22)
        minuto_random = random.randint(0, 59)

        # Data de check-in no passado
        data_checkin = datetime.now() - timedelta(days=dias_atras, hours=hora_random, minutes=minuto_random)

        # Duração aleatória entre 30 e 120 minutos
        duracao_minutos = random.randint(30, 120)
        data_checkout = data_checkin + timedelta(minutes=duracao_minutos)

        cur.execute("""
            INSERT INTO checkins (aluno_id, data_checkin, data_checkout)
            VALUES (%s, %s, %s)
        """, (aluno_id, data_checkin, data_checkout))

con.commit()
cur.close()
con.close()

print("Dados sintéticos inseridos com sucesso!")
