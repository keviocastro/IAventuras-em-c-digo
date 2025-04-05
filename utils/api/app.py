from fastapi import FastAPI
from fastapi import Form
import pandas as pd
import logging
import pickle

from db.crud import PostgreSQLDatabase
from config.constants import EnvVars, DatetimeFormats

env = EnvVars()
db_password = env.get_var("DB_PASSWORD")
dt =    DatetimeFormats()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

db = PostgreSQLDatabase(
    user="juanml",
    dbname="churnml",
    password=db_password,
    host="localhost",
    port="5432"
)

with open("src/models/model.pkl", "rb") as f:
    model = pickle.load(f)

app = FastAPI()

@app.post("/aluno/registro")
def register(name: str = Form(...), age: int = Form(...)):
    try:
        db.insert(
            "alunos",
            {
                "nome_aluno": name,
                "idade_aluno": age
            }
        )
        logging.info("A new gym-attender has been successfully registered.")
        return {"status": "sucesso", "mensagem": "Aluno registrado com sucesso"}
    except Exception as e:
        logging.error(f"Error: {e}")


@app.post("/aluno/checkin")
def checkin(id_aluno: int):
    db.insert(
        "checkins",
        {
            "id_aluno": id_aluno,
            "data_checkin": dt.get_datetime()
        }
    )


@app.get("/aluno/{id_aluno}/frequencia")
def get_frequency(id_aluno: int):
    if db.connect_db():
        try:
            query = """
                SELECT 
                    a.nome_aluno,
                    c.data_checkin,
                    c.data_checkout,
                    p.nome_plano,
                    m.data_inicio AS inicio_matricula,
                    m.data_fim AS fim_matricula
                FROM checkins c
                JOIN alunos a ON c.id_aluno = a.id_aluno
                LEFT JOIN matriculas m ON c.id_aluno = m.id_aluno
                    AND c.data_checkin::DATE BETWEEN m.data_inicio AND COALESCE(m.data_fim, CURRENT_DATE)
                LEFT JOIN planos p ON m.id_plano = p.id_plano
                WHERE a.id_aluno = %s
                ORDER BY c.data_checkin DESC
            """
            db.cursor.execute(query, (id_aluno,))
            resultados = db.cursor.fetchall()

            colunas = [desc[0] for desc in db.cursor.description]
            historico = [dict(zip(colunas, linha)) for linha in resultados]

            return historico

        except Exception as e:
            logging.error(f"Erro ao buscar frequência do aluno {id_aluno}: {e}")
            return []
        finally:
            db.close_db()
    else:
        return []

def get_model_features(id_aluno):
    if not db.connect_db():
        return None

    query = """
        SELECT 
            a.id_aluno,
            a.nome_aluno,
            p.nome_plano,
            c.data_checkin,
            c.data_checkout,
            m.data_inicio,
            m.data_fim
        FROM alunos a
        LEFT JOIN checkins c ON a.id_aluno = c.id_aluno
        LEFT JOIN matriculas m ON a.id_aluno = m.id_aluno
            AND c.data_checkin::DATE BETWEEN m.data_inicio AND COALESCE(m.data_fim, CURRENT_DATE)
        LEFT JOIN planos p ON m.id_plano = p.id_plano
        WHERE a.id_aluno = %s
    """
    db.cursor.execute(query, (id_aluno,))
    rows = db.cursor.fetchall()
    colunas = [desc[0] for desc in db.cursor.description]
    db.close_db()

    if not rows:
        return None

    df = pd.DataFrame(rows, columns=colunas)
    
    df["data_checkin"] = pd.to_datetime(df["data_checkin"])
    df["data_checkout"] = pd.to_datetime(df["data_checkout"])
    df["data_inicio"] = pd.to_datetime(df["data_inicio"])

    # frequência semanal
    ultimo_checkin = df["data_checkin"].max()
    semanas = max((ultimo_checkin - df["data_inicio"].min()).days / 7, 1)
    total_checkins = df["data_checkin"].count()
    frequencia_semanal = total_checkins / semanas

    # tempo desde o último checkin
    tempo_desde_ultimo_checkin = (pd.Timestamp.now() - ultimo_checkin).days

    # duração média das visitas
    df["duracao_visita"] = (df["data_checkout"] - df["data_checkin"]).dt.total_seconds() / 60
    duracao_media = df["duracao_visita"].mean()

    # tipo do plano
    plano = df["nome_plano"].iloc[0]
    plano = plano.lower()
    tipo_plano_mensal = int("mensal" in plano)
    tipo_plano_semestral = int("semestral" in plano)

    features = pd.DataFrame([{
        "frequencia_semanal": frequencia_semanal,
        "tempo_desde_ultimo_checkin": tempo_desde_ultimo_checkin,
        "duracao_media_visitas": duracao_media,
        "tipo_plano_Mensal": tipo_plano_mensal,
        "tipo_plano_Semestral": tipo_plano_semestral
    }])

    return features

@app.get("/aluno/{id}/risco-churn")
def risco_churn(id: int):
    features = get_model_features(id)
    
    if features is None:
        return {"status": "erro", "mensagem": "Aluno não encontrado ou sem dados suficientes."}

    probabilidade = model.predict_proba(features)[0][1]
    
    return {
        "id_aluno": id,
        "probabilidade_churn": round(float(probabilidade), 4),
        "interpretacao": (
            "Alto risco" if probabilidade >= 0.7 else
            "Risco moderado" if probabilidade >= 0.4 else
            "Baixo risco"
        )
    }