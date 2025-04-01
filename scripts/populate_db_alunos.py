import csv
import os
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app.models.database import engine
from app.models import Aluno
from datetime import datetime

# Obtém o diretório do script
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, "../alunos.csv")

session = Session(bind=engine)

with open(csv_path, "r") as f:
    reader = csv.reader(f)
    next(reader)  # Pular cabeçalho

    alunos = []
    for row in reader:
        matricula, nome, data_nascimento, genero, email, plano_id, data_matricula, matricula_ativa, data_cancelamento = row

        aluno = {
            "matricula": int(matricula),
            "nome": nome,
            "data_nascimento": datetime.strptime(data_nascimento, "%Y-%m-%d").date() if data_nascimento else None,
            "genero": genero if genero else None,
            "email": email,
            "plano_id": int(plano_id),
            "data_matricula": datetime.strptime(data_matricula, "%Y-%m-%d").date(),
            "matricula_ativa": matricula_ativa.lower() == "true",
            "data_cancelamento": datetime.strptime(data_cancelamento, "%Y-%m-%d").date() if data_cancelamento else None
        }
        alunos.append(aluno)

    stmt = insert(Aluno).values(alunos).on_conflict_do_nothing(index_elements=["email"])
    session.execute(stmt)
    session.commit()
    print("Alunos adicionados com sucesso!")

# Fechando a sessão
session.close()
