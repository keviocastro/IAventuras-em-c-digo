from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import psycopg2
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

# ----------------------------
# Modelo para entrada
# ----------------------------
class CheckinRequest(BaseModel):
    aluno_id: int = Field(..., example=1, description="ID do aluno que está fazendo o check-in")

# ----------------------------
# Endpoint para registrar check-in manual
# ----------------------------
@router.post("/", summary="Registrar entrada do aluno")
def registrar_checkin(req: CheckinRequest):
    """
    Registra a entrada de um aluno na academia (check-in manual).
    """
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute("INSERT INTO checkins (aluno_id) VALUES (%s)", (req.aluno_id,))
        con.commit()
        cur.close()
        con.close()
        return {"mensagem": "Check-in registrado com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))