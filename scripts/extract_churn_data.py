import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.database import SessionLocal
from app.models import Aluno, Checkin
from datetime import datetime, timedelta

def calcular_metricas_churn(db: Session):
    hoje = datetime.utcnow()
    dados = []

    alunos = db.query(Aluno).all()
    for aluno in alunos:
        checkins = db.query(Checkin).filter(Checkin.aluno_id == aluno.matricula).all()

        if checkins:
            datas_checkins = [c.data_hora_entrada for c in checkins]
            datas_checkins.sort()
            
            # Frequência semanal
            primeira_data = datas_checkins[0]
            semanas = max(1, (hoje - primeira_data).days // 7)
            frequencia_semanal = len(checkins) / semanas
            
            # Tempo desde o último check-in
            tempo_ultimo_checkin = (hoje - datas_checkins[-1]).days
            
            # Duração média das visitas
            duracoes = [(c.data_hora_saida - c.data_hora_entrada).total_seconds() / 60 
                        for c in checkins if c.data_hora_saida]
            duracao_media = sum(duracoes) / len(duracoes) if duracoes else 0
        else:
            frequencia_semanal = 0
            hoje = datetime.today().date()  # Garantir que 'hoje' seja do tipo 'date'
            tempo_ultimo_checkin = (hoje - aluno.data_matricula).days

            duracao_media = 0
        
        # Status de matrícula (churn: 1 se cancelado, 0 se ativo)
        churn = 1 if aluno.data_cancelamento else 0
        
        dados.append([
            aluno.matricula, aluno.plano_id, frequencia_semanal,
            tempo_ultimo_checkin, duracao_media, churn
        ])
    
    return pd.DataFrame(dados, columns=[
        "matricula", "plano_id", "frequencia_semanal",
        "tempo_ultimo_checkin", "duracao_media", "churn"
    ])

if __name__ == "__main__":
    db = SessionLocal()
    df = calcular_metricas_churn(db)
    df.to_csv("dados_churn.csv", index=False)
    print("Arquivo dados_churn.csv gerado com sucesso!")
    db.close()
