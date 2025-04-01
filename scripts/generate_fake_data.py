import csv
import random
from datetime import datetime, timedelta, date
from faker import Faker

fake = Faker()
random.seed(42)

# Parâmetros
total_alunos = 2000
planos_ids = [1, 2, 3]  # IDs dos planos

# Gerar alunos
alunos = []
for i in range(1, total_alunos + 1):
    nome = fake.name()
    data_nascimento = fake.date_of_birth(minimum_age=18, maximum_age=60).strftime("%Y-%m-%d")
    genero = random.choice(["Masculino", "Feminino", "Outro"])
    email = fake.email()
    plano_id = random.choice(planos_ids)
    data_matricula = fake.date_between(start_date="-2y", end_date="today")

    matricula_ativa = random.choice([True, False])

    data_cancelamento = None
    if not matricula_ativa:
        data_cancelamento = fake.date_between(start_date=data_matricula, end_date=date.today()).strftime("%Y-%m-%d")

    alunos.append([
        i, nome, data_nascimento, genero, email, plano_id,
        data_matricula.strftime("%Y-%m-%d"), matricula_ativa, data_cancelamento
    ])

# Salvar alunos.csv
with open("alunos.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["matricula", "nome", "data_nascimento", "genero", "email", "plano_id", "data_matricula", "matricula_ativa", "data_cancelamento"])
    writer.writerows(alunos)

# Gerar check-ins
checkins = []
for aluno in alunos:
    matricula, _, _, _, _, _, data_matricula, matricula_ativa, data_cancelamento = aluno
    data_matricula = datetime.strptime(data_matricula, "%Y-%m-%d")

    if not matricula_ativa and data_cancelamento is not None:
        data_fim = datetime.strptime(data_cancelamento, "%Y-%m-%d")
    else:
        data_fim = datetime.today()
    
    num_checkins = random.randint(5, 75)
    for _ in range(num_checkins):
        data_entrada = fake.date_time_between(start_date=data_matricula, end_date=data_fim)
        data_saida = data_entrada + timedelta(hours=random.randint(1, 3))
        checkins.append([
            matricula, data_entrada.strftime("%Y-%m-%d %H:%M:%S"), data_saida.strftime("%Y-%m-%d %H:%M:%S")
        ])

# Salvar checkins.csv
with open("checkins.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["aluno_id", "data_hora_entrada", "data_hora_saida"])
    writer.writerows(checkins)

print("Arquivos alunos.csv e checkins.csv gerados com sucesso!")
