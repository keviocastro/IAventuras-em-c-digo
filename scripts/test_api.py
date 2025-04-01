import requests
import random
from datetime import datetime
from time import sleep

BASE_URL = "http://localhost:8000"

# 1. Criar alunos de teste
def criar_alunos():
    alunos_ids = []
    for i in range(10):
        aluno = {
            "nome": f"Aluno Teste {i+1}",
            "email": f"aluno{i+1}@teste.com",
            "data_nascimento": "1990-01-01",
            "plano_id": random.choice([1, 2, 3])
        }
        r = requests.post(f"{BASE_URL}/aluno/registro", json=aluno)
        resp = r.json()
        print("🎓 Aluno:", r.status_code, resp)
        if r.status_code == 200 and "aluno_id" in resp:
            alunos_ids.append(resp["aluno_id"])
    return alunos_ids

# 2. Registrar check-in manual
def registrar_checkins(alunos_ids):
    for aluno_id in alunos_ids:
        r = requests.post(f"{BASE_URL}/checkin", json={"aluno_id": aluno_id})
        print(f"✅ Check-in aluno {aluno_id}:", r.status_code, r.json())
        sleep(0.3)

# 3. Enviar tarefas reais
def enviar_tarefas(alunos_ids):
    # Enviar check-ins em massa
    payload_checkin = {
        "alunos": alunos_ids,
        "data_checkin": datetime.now().isoformat()
    }
    r1 = requests.post(f"{BASE_URL}/tarefas/checkins", json=payload_checkin)
    print(f"📦 Check-in em massa: {r1.status_code} - {r1.json()}")

    sleep(1)

    # Gerar relatório
    r2 = requests.post(f"{BASE_URL}/tarefas/relatorio")
    print(f"📊 Relatório: {r2.status_code} - {r2.json()}")

    sleep(1)

    # Atualizar churn
    r3 = requests.post(f"{BASE_URL}/tarefas/churn")
    print(f"🧠 Churn: {r3.status_code} - {r3.json()}")

# Execução principal
if __name__ == "__main__":
    print("🚀 Iniciando teste completo...")
    alunos = criar_alunos()
    if alunos:
        registrar_checkins(alunos)
        enviar_tarefas(alunos)
        print("✅ Teste concluído com sucesso.")
    else:
        print("⚠️ Nenhum aluno criado. Teste abortado.")
