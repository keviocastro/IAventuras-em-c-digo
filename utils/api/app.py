from fastapi import FastAPI
from fastapi import Form
import logging

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

    except Exception as e:
        logging.error(f"Error: {e}")

@app.post("/aluno/checkin")
def checkin(id_aluno: str = Form(...)):
    db.insert(
        "checkins",
        {
            "id_aluno": id_aluno,
            "data_checkin": dt.get_datetime()
        }
    )


@app.get("/aluno/{id}/frequencia")
def get_frequency(id_aluno: str = Form(...)):
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

@app.get("/aluno/{id}/risco-churn")
def get_churn_prob():
    pass