from fastapi import APIRouter, Body
from app.producer import send_to_queue

router = APIRouter()

# ----------------------------
# Endpoint para registrar check-in em massa
# ----------------------------
@router.post("/checkins", summary="Processar check-ins em massa")
def processar_checkins_em_massa(payload: dict = Body(...)):
    """
    Espera um payload como:
    {
        "alunos": [1, 2, 3],
        "data_checkin": "2025-03-30T14:30:00"
    }
    """
    send_to_queue("fila_checkin", payload)
    return {"mensagem": "Check-ins enviados para a fila"}


# ----------------------------
# Endpoint para registrar check-outs em massa
# ----------------------------
@router.post("/checkout", summary="Processar checkouts em massa")
def processar_checkouts_em_massa(payload: dict = Body(...)):
    """
    Envia um payload com lista de alunos para a fila 'fila_checkout'.
    Esperado:
    {
        "alunos": [1, 2, 3]
    }
    """
    send_to_queue("fila_checkout", payload)
    return {"mensagem": "Checkouts enviados para a fila"}

# ----------------------------
# Endpoint para gerar relatório de frequência
# ----------------------------
@router.post("/relatorio", summary="Gerar relatório de frequência")
def gerar_relatorio():
    """
    Dispara uma tarefa para gerar o relatório diário de frequência dos alunos.

    - O relatório incluirá todos os check-ins feitos no **dia atual**.
    - O arquivo será salvo na pasta `relatorios/` com nome no formato `relatorio_frequencia_YYYYMMDD.csv`.
    - A lógica de geração está no worker `worker_relatorio.py`.
    """
    send_to_queue("fila_relatorio", {"acao": "gerar_relatorio"})
    return {"mensagem": "Solicitação enviada para gerar relatório"}


# ----------------------------
# Endpoint para atualizar modelo de churn
# ----------------------------
@router.post("/churn", summary="Atualizar modelo de churn")
def atualizar_modelo_churn():
    """
    Dispara uma tarefa para treinar e atualizar o modelo de previsão de churn dos alunos.

    - O modelo será treinado com base nos últimos check-ins.
    - Será salvo em `modelos/modelo_churn.pkl`.
    - Essa operação é executada no worker `worker_churn.py`.
    """
    send_to_queue("fila_churn", {"acao": "atualizar_modelo"})
    return {"mensagem": "Solicitação enviada para atualizar modelo de churn"}