from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from datetime import datetime
import pandas as pd
import psycopg2
import pickle
import json
import os

# ----------------------------
# Configuração do banco
# ----------------------------
dir_atual = os.path.dirname(__file__)
dir_pai = os.path.dirname(dir_atual)
dir_avo = os.path.dirname(dir_pai)

config_path = os.path.join(dir_avo, "banco.json")

with open(config_path, "r") as f:
    db_config = json.load(f)

def get_connection():
    return psycopg2.connect(**db_config)

# ----------------------------
# Inicializa o router
# ----------------------------
router = APIRouter()

# ---------------------
# MODELOS
# ---------------------
class AlunoCreate(BaseModel):
    nome: str = Field(..., example="João da Silva")
    email: str = Field(..., example="joao@email.com")
    data_nascimento: str = Field(..., example="1990-05-12", description="Data no formato YYYY-MM-DD")
    plano_id: int = Field(..., example=1)

    class Config:
        json_schema_extra = {
            "example": {
                "nome": "Maria Oliveira",
                "email": "maria@email.com",
                "data_nascimento": "1988-11-23",
                "plano_id": 2
            }
        }

class CheckinRequest(BaseModel):
    aluno_id: int = Field(..., example=42)

# ---------------------
# ENDPOINTS
# ---------------------

# ----------------------------
# Endpoint para registrar novo aluno
# ----------------------------
@router.post("/registro", summary="Registrar novo aluno", response_description="Aluno criado com sucesso")
def registrar_aluno(aluno: AlunoCreate):
    """
    Registra um novo aluno na base de dados da academia.
    """
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            INSERT INTO alunos (nome, email, data_nascimento, plano_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (aluno.nome, aluno.email, aluno.data_nascimento, aluno.plano_id))
        aluno_id = cur.fetchone()[0]
        con.commit()
        cur.close()
        con.close()
        return {"mensagem": "Aluno registrado com sucesso", "aluno_id": aluno_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ----------------------------
# Endpoint para retornar dados de frequência do aluno
# ----------------------------
@router.get("/{id}/frequencia", summary="Histórico de check-ins do aluno")
def obter_frequencia(id: int = Path(..., description="ID do aluno", example=42)):
    """
    Retorna o histórico de frequência (check-ins) do aluno, ordenado da data mais recente para a mais antiga.
    """
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT data_checkin
            FROM checkins
            WHERE aluno_id = %s
            ORDER BY data_checkin DESC
        """, (id,))
        resultados = cur.fetchall()
        cur.close()
        con.close()
        return {"aluno_id": id, "checkins": [r[0].isoformat() for r in resultados]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----------------------------
# Endpoint para verificar risco de churn (desistência)
# ----------------------------
@router.get("/{id}/risco-churn", summary="Obter risco de churn via modelo")
def risco_churn(id: int = Path(..., description="ID do aluno", example=42)):
    """
    Utiliza o modelo treinado para prever a probabilidade de churn de um aluno com base em:
    - Dias sem check-in
    - Frequência semanal
    - Duração média das visitas
    - Tipo de plano
    """
    try:
        # ---------------------------
        # Conectar e buscar métricas do aluno
        # ---------------------------
        con = get_connection()
        query = """
            SELECT 
                a.id AS aluno_id,
                a.plano_id,
                MAX(c.data_checkin) AS ultimo_checkin,
                COUNT(*) FILTER (WHERE c.data_checkin >= NOW() - INTERVAL '28 days') / 4.0 AS freq_semanal,
                AVG(EXTRACT(EPOCH FROM c.duracao)/60.0) AS duracao_media
            FROM alunos a
            LEFT JOIN checkins c ON a.id = c.aluno_id
            WHERE a.id = %s
            GROUP BY a.id, a.plano_id
        """
        df = pd.read_sql_query(query, con, params=(id,))
        con.close()

        if df.empty:
            return {"aluno_id": id, "risco_churn": "alto", "motivo": "Aluno não encontrado ou sem check-ins"}

        df["dias_sem_checkin"] = (datetime.now() - df["ultimo_checkin"]).dt.days.fillna(999)
        df["freq_semanal"] = df["freq_semanal"].fillna(0)
        df["duracao_media"] = df["duracao_media"].fillna(0)

        # ---------------------------
        # Preparar entrada para o modelo
        # ---------------------------
        X_input = df[["dias_sem_checkin", "freq_semanal", "duracao_media", "plano_id"]]
        X_encoded = pd.get_dummies(X_input)

        # ---------------------------
        # Carregar modelo treinado
        # ---------------------------
        modelo_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),  # sobe de alunos.py → routes → app → raiz
        "modelos",
        "modelo_churn.pkl"
        )

        if not os.path.exists(modelo_path):
            print(f"❌ Modelo não encontrado no caminho: {modelo_path}")
            raise HTTPException(
                status_code=500,
                detail=f"Modelo de churn não encontrado. Execute o treinamento primeiro.\nCaminho verificado: {modelo_path}"
            )

        with open(modelo_path, "rb") as f:
            modelo = pickle.load(f)

        # ---------------------------
        # Alinhar colunas com as do modelo (em caso de plano_id faltante)
        # ---------------------------
        modelo_cols = modelo.named_steps["clf"].feature_names_in_
        for col in modelo_cols:
            if col not in X_encoded.columns:
                X_encoded[col] = 0  # adiciona colunas faltantes com 0
        X_encoded = X_encoded[modelo_cols]  # garante mesma ordem

        # ---------------------------
        # Previsão e resposta
        # ---------------------------
        prob = modelo.predict_proba(X_encoded)[0][1]  # probabilidade de churn

        if prob > 0.7:
            risco = "alto"
        elif prob > 0.4:
            risco = "moderado"
        else:
            risco = "baixo"

        return {
            "aluno_id": id,
            "dias_sem_frequencia": int(df['dias_sem_checkin'].values[0]),
            "frequencia_semanal": float(df["freq_semanal"].values[0]),
            "duracao_media": float(df["duracao_media"].values[0]),
            "plano_id": int(df["plano_id"].values[0]),
            "probabilidade_churn": round(prob, 4),
            "risco_churn": risco
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))