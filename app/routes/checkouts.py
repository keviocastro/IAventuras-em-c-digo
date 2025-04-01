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
class CheckoutRequest(BaseModel):
    aluno_id: int = Field(..., example=1, description="ID do aluno que está fazendo o check-out")

# ----------------------------
# Endpoint para registrar saída (checkout)
# ----------------------------
@router.post("/", summary="Registrar saída do aluno")
def registrar_checkout(req: CheckoutRequest):
    """
    Registra a saída de um aluno na academia (checkout).
    Atualiza o último check-in do aluno que ainda não possui `data_checkout`.
    """
    try:
        con = get_connection()
        cur = con.cursor()

        # Atualiza o último check-in SEM data_checkout preenchida
        cur.execute("""
            UPDATE checkins
            SET data_checkout = CURRENT_TIMESTAMP
            WHERE id = (
                SELECT id FROM checkins
                WHERE aluno_id = %s AND data_checkout IS NULL
                ORDER BY data_checkin DESC
                LIMIT 1
            )
        """, (req.aluno_id,))

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Nenhum check-in aberto encontrado para este aluno.")

        con.commit()
        cur.close()
        con.close()
        return {"mensagem": "Checkout registrado com sucesso"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
