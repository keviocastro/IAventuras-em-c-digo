from fastapi import APIRouter

router = APIRouter()

@router.post("/aluno/registro")
async def registrar_aluno():
    return {"message": "Aluno registrado com sucesso"}

@router.post("/aluno/checkin")
async def registrar_checkin():
    return {"message": "Check-in realizado"}

@router.get("/aluno/{id}/frequencia")
async def obter_frequencia(id: int):
    return {"aluno_id": id, "frequencia": "dados de frequência aqui"}

@router.get("/aluno/{id}/risco-churn")
async def prever_churn(id: int):
    return {"aluno_id": id, "risco_churn": "probabilidade calculada"}