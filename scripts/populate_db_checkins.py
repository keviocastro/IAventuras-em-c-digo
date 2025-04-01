import csv
import os
from sqlalchemy.orm import Session
from app.models.database import engine
from app.models import Checkin, Aluno
from datetime import datetime

# Obtém o diretório do script
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, "../checkins.csv")

session = Session(bind=engine)

with open(csv_path, "r") as f:
    reader = csv.reader(f)
    next(reader)  # Pular cabeçalho
    
    for row in reader:
        aluno_id, data_hora_entrada, data_hora_saida = row
        
        # Verificar se o aluno_id existe na tabela Aluno
        aluno = session.query(Aluno).filter_by(matricula=int(aluno_id)).first()
        
        if aluno:  # Só adicionar o check-in se o aluno existir
            checkin = Checkin(
                aluno_id=int(aluno_id),
                data_hora_entrada=datetime.strptime(data_hora_entrada, "%Y-%m-%d %H:%M:%S"),
                data_hora_saida=datetime.strptime(data_hora_saida, "%Y-%m-%d %H:%M:%S") if data_hora_saida else None
            )
            session.add(checkin)
        else:
            print(f"Aviso: Aluno com matrícula {aluno_id} não encontrado. Check-in ignorado.")
    
    session.commit()
    print("Check-ins adicionados com sucesso!")

# Fechando a sessão
session.close()
