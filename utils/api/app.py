from fastapi import (
    FastAPI,
    Path,
    HTTPException
)
from pydantic import BaseModel
import datetime
import pandas as pd
import logging
import pickle

from utils.db.crud import PostgreSQLDatabase
from config.project_constants import EnvVars
from config.project_constants import DatetimeFormats as dt
from utils.messaging.producer import send_to_checkin_queue

env = EnvVars()
db_password = env.get_var("DB_PASSWORD")
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

class CheckinPayload(BaseModel):
    id_aluno: int

class Aluno(BaseModel):
    id: int
    name: str
    age: int

class Planos(BaseModel):
    name: str
    type: str
    price: float

class Matriculas(BaseModel):
    attender_id: int
    plan_id: int
    status: bool

class Checkins(BaseModel):
    id: int

class Checkouts(BaseModel):
    id: int

@app.post("/aluno/registro")
def register(aluno: Aluno, plano: Planos, matricula: Matriculas):
    try:
        if not db.connect_db():
            logging.error("Erro to conect Database")
            return {"status": "erro", "mensagem": "Erro ao conectar ao banco de dados"}

        db.cursor.execute(
            """
            INSERT INTO alunos (nome_aluno, idade_aluno)
            VALUES (%s, %s)
            RETURNING id_aluno
            """,
            (aluno.name, aluno.age)
        )
        id_aluno = db.cursor.fetchone()[0]

        existing_plan = db.read(
            table_name="planos",
            cols=["id_plano"],
            condition=f"nome_plano = '{plano.name}'"
        )

        if existing_plan:
            id_plano = existing_plan[0][0]
        else:
            db.cursor.execute(
                """
                INSERT INTO planos (nome_plano, tipo_plano, valor_plano)
                VALUES (%s, %s, %s)
                RETURNING id_plano
                """,
                (plano.name, plano.type, plano.price)
            )
            id_plano = db.cursor.fetchone()[0]

        db.insert(
            "matriculas",
            {
                "id_aluno": id_aluno,
                "id_plano": id_plano,
                "data_inicio": dt.get_datetime(),
                "data_fim": dt.get_datetime_plus_6_months(),
                "ativa": matricula.status
            }
        )

        db.close_db()
        logging.info("A new gym-attender has been successfully registered.")
        return {"status": "sucesso", "mensagem": "Aluno registrado com sucesso"}
    except Exception as register_error:
        logging.error(f"Register Error: {register_error}")

@app.post("/aluno/checkin")
def checkin(payload: CheckinPayload):
    aluno_id = payload.id_aluno
    message = {
        "id_aluno": aluno_id,
        "timestamp_requisicao": datetime.datetime.now().isoformat()
    }
    logging.info(f"Recebida requisição de check-in para aluno ID: {aluno_id}")

    try:
        sucesso_envio = send_to_checkin_queue(message)
        if not sucesso_envio:
             logging.error(f"Falha ao enviar check-in para a fila para aluno ID: {aluno_id}")
             raise HTTPException(status_code=500, detail="Erro interno ao processar o check-in. Tente novamente mais tarde.")

        logging.info(f"Check-in para aluno ID: {aluno_id} enfileirado com sucesso.")
        return {"status": "sucesso", "mensagem": "Check-in recebido e sendo processado."}

    except Exception as api_error:
        logging.error(f"Erro inesperado no endpoint /aluno/checkin: {api_error}")
        raise HTTPException(status_code=500, detail="Erro inesperado no servidor.")

@app.post("/aluno/checkout")
def checkout(aluno_id: Checkouts):
    try:
        if not db.connect_db():
            logging.error("Error to conect Database")
            return {"status": "error", "mensagem": "Error to conect Database"}

        db.insert(
            "checkouts",
            {
                "id_aluno": aluno_id.id,
                "data_checkout": dt.get_datetime()
            }
        )
        logging.info("Checkout registered. Hope you enjoy it and see you soon!")
        return {"status": "sucesso", "mensagem": "Checkout realizado com sucesso!"}
    except Exception as checkout_error:
        logging.error(f"Checkout Error: {checkout_error}")

@app.get("/aluno/{id}/frequencia")
def get_frequency(id: int = Path(..., description="ID do aluno")):
    if db.connect_db():
        try:
            query = """
                SELECT 
                    a.nome_aluno,
                    ci.data_checkin,
                    co.data_checkout,
                    p.nome_plano,
                    m.data_inicio AS inicio_matricula,
                    m.data_fim AS fim_matricula
                FROM checkins ci
                JOIN alunos a ON ci.id_aluno = a.id_aluno
                LEFT JOIN checkouts co ON co.id_aluno = ci.id_aluno
                    AND co.data_checkout > ci.data_checkin
                LEFT JOIN matriculas m ON ci.id_aluno = m.id_aluno
                    AND ci.data_checkin::DATE BETWEEN m.data_inicio AND COALESCE(m.data_fim, CURRENT_DATE)
                LEFT JOIN planos p ON m.id_plano = p.id_plano
                WHERE a.id_aluno = %s
                ORDER BY ci.data_checkin DESC;

            """
            db.cursor.execute(query, (id,))
            resultados = db.cursor.fetchall()

            colunas = [desc[0] for desc in db.cursor.description]
            historico = [dict(zip(colunas, linha)) for linha in resultados]

            return historico

        except Exception as e:
            logging.error(f"Erro ao buscar frequência do aluno {id}: {e}")
            return []
        finally:
            db.close_db()
    else:
        return []

def get_model_features(id: int = Path(..., description="ID do aluno")):
    if not db.connect_db():
        return None
    
    check_query = "SELECT id_aluno FROM alunos WHERE id_aluno = %s" # primeiro verifica se o aluno existe no banco de dados
    db.cursor.execute(check_query, (id,))
    if not db.cursor.fetchone():
        db.close_db()
        return None
    
    query = """
    SELECT
        a.id_aluno,
        a.nome_aluno,
        p.nome_plano,
        ci.data_checkin,
        co.data_checkout,
        m.data_inicio,
        m.data_fim
    FROM alunos a
    LEFT JOIN matriculas m ON a.id_aluno = m.id_aluno
    LEFT JOIN planos p ON m.id_plano = p.id_plano
    LEFT JOIN checkins ci ON a.id_aluno = ci.id_aluno
    LEFT JOIN checkouts co ON a.id_aluno = co.id_aluno
        AND co.data_checkout > ci.data_checkin
        AND co.data_checkout = (
            SELECT MIN(co2.data_checkout) 
            FROM checkouts co2 
            WHERE co2.id_aluno = ci.id_aluno 
            AND co2.data_checkout > ci.data_checkin
        )
    WHERE a.id_aluno = %s
    """
    db.cursor.execute(query, (id,))
    rows = db.cursor.fetchall()
    colunas = [desc[0] for desc in db.cursor.description]
    db.close_db()
    
    if not rows:
        return None
    
    df = pd.DataFrame(rows, columns=colunas)
    
    df["data_checkin"] = pd.to_datetime(df["data_checkin"], errors='coerce').dt.tz_localize(None)
    df["data_checkout"] = pd.to_datetime(df["data_checkout"], errors='coerce').dt.tz_localize(None)
    df["data_inicio"] = pd.to_datetime(df["data_inicio"], errors='coerce').dt.tz_localize(None)
    
    now = pd.Timestamp.now().tz_localize(None)
    
    if df["data_checkin"].count() == 0:
        return pd.DataFrame([{
            "frequencia_semanal": 0,
            "tempo_desde_ultimo_checkin": 30,  # valor alto para indicar inatividade
            "duracao_media_visitas": 0,
            "tipo_plano_Mensal": int("mensal" in df["nome_plano"].iloc[0].lower()) if not pd.isna(df["nome_plano"].iloc[0]) else 0,
            "tipo_plano_Semestral": int("semestral" in df["nome_plano"].iloc[0].lower()) if not pd.isna(df["nome_plano"].iloc[0]) else 0
        }])
    
    ultimo_checkin = df["data_checkin"].max()
    data_inicio = df["data_inicio"].min()
    
    if pd.isna(data_inicio):
        data_inicio = df["data_checkin"].min()
    
    dias_ativos = max((ultimo_checkin - data_inicio).days, 1)
    semanas = max(dias_ativos / 7, 1)
    total_checkins = df["data_checkin"].count()
    frequencia_semanal = total_checkins / semanas
    
    tempo_desde_ultimo_checkin = (now - ultimo_checkin).days
    
    df_com_checkout = df.dropna(subset=["data_checkout"])
    
    if len(df_com_checkout) > 0:
        df_com_checkout["duracao_visita"] = (df_com_checkout["data_checkout"] - df_com_checkout["data_checkin"]).dt.total_seconds() / 60
        duracao_media = df_com_checkout["duracao_visita"].mean()
    else:
        duracao_media = 0  # valor padrão se não houver checkouts
    
    plano = ""
    if not pd.isna(df["nome_plano"].iloc[0]):
        plano = df["nome_plano"].iloc[0].lower()
    
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
def risco_churn(id: int = Path(..., description="ID do aluno")):
    try:
        features = get_model_features(id)
        if features is None:
            return {"status": "erro", "mensagem": "Aluno não encontrado ou sem dados suficientes."}
            
        required_features = ["frequencia_semanal", "tempo_desde_ultimo_checkin", 
                             "duracao_media_visitas", "tipo_plano_Mensal", "tipo_plano_Semestral"]
        
        for feature in required_features:
            if feature not in features.columns:
                return {"status": "erro", "mensagem": f"Feature {feature} não disponível para o modelo."}
                
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
    except Exception as e:
        # log para debug mais detalhado
        import traceback
        print(f"Erro detalhado: {traceback.format_exc()}")
        return {"status": "erro", "mensagem": f"Erro ao calcular risco de churn: {str(e)}"}