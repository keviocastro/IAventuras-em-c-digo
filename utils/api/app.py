from fastapi import (
    FastAPI,
    Path,
    HTTPException
)
import datetime
import logging
import pickle

from utils.db.crud import PostgreSQLDatabase
from config.project_constants import EnvVars
from config.project_constants import DatetimeFormats as dt
from utils.api.schema import models as schema
from utils.api.ml import get_model_features
from utils.messaging.producer import send_to_checkin_queue
from utils.model.load_model import get_current_model

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

@app.post("/aluno/registro", summary="Registrar novo aluno", description="Registra um novo aluno com seus dados, plano e matrícula.")
def register(aluno: schema.Aluno, plano: schema.Planos, matricula: schema.Matriculas):
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

@app.post("/aluno/checkin", summary="Check-in do aluno", description="Registra um check-in do aluno na academia.")
def checkin(payload: schema.CheckinPayload):
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

@app.post("/aluno/checkout", summary="Check-out do aluno", description="Registra um check-out do aluno na academia.", response_model=schema.ResponseStatus)
def checkout(aluno_id: schema.Checkouts):
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

@app.get("/aluno/{id}/frequencia", summary="Relatório com Histórico de Frequência", description="Este endpoint gera um relatório com o histórico de frequência de um aluno.")
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

@app.get("/aluno/{id}/risco-churn", summary="Probabilidade de Churn", description="Este endpoint retorna a probabilidade de um aluno cancelar sua inscrição.")
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
        
        model = get_current_model() # pra carregar o modelo mais recente
        if model is None:
            return {"status": "erro", "mensagem": "Erro ao carregar o modelo de previsão."}
                
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
