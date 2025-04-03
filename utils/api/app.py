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
def checkin():
    db.insert(
        "checkins",
        {
            "data_checkin": dt.get_datetime()
        }
    )


@app.get("/aluno/{id}/frequencia")
def get_frequency():
    pass

@app.get("/aluno/{id}/risco-churn")
def get_churn_prob():
    pass

