from app.database import SessionLocal
from app.models import Aluno, checkins
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import pandas as pd
from datetime import date, timedelta
import joblib

def calcular_features(db, alunos):
    """Calcula as features para o modelo de churn de forma otimizada."""
    data = []

    checkins_por_aluno = db.query(checkins).filter(
        checkins.aluno_id.in_([aluno.id for aluno in alunos])
    ).all()

    checkins_dict = {}
    for checkin in checkins_por_aluno:
        if checkin.aluno_id not in checkins_dict:
            checkins_dict[checkin.aluno_id] = []
        checkins_dict[checkin.aluno_id].append(checkin)

    # Calcula features para cada aluno
    for aluno in alunos:

        checkins_aluno = checkins_dict.get(aluno.id, [])

        # Frequência semanal
        frequencia_semanal = sum(
            1 for checkin in checkins_aluno
            if checkin.data >= date.today() - timedelta(days=7)
        )

        # Tempo desde o último check-in
        ultimo_checkin = max(
            (checkin.data for checkin in checkins_aluno),
            default=None
        )
        tempo_ultimo_checkin = (date.today() - ultimo_checkin).days if ultimo_checkin else 30

        # Duração média das visitas
        duracoes = [
            (checkin.horario_checkout.hour * 60 + checkin.horario_checkout.minute) -
            (checkin.horario_checkin.hour * 60 + checkin.horario_checkin.minute)
            for checkin in checkins_aluno
            if checkin.horario_checkin and checkin.horario_checkout
        ]
        duracao_media_visitas = sum(duracoes) / len(duracoes) if duracoes else 0

        PLANO_MAP = {"Básico": 1, "Premium": 2, "Avançado": 3}
        tipo_plano = PLANO_MAP.get(aluno.plano, -1)

        # Adicione os dados para o modelo
        data.append([frequencia_semanal, tempo_ultimo_checkin, duracao_media_visitas, tipo_plano])
