from fastapi import FastAPI
from app.routes import alunos, checkins, tarefas, checkouts

app = FastAPI(
    title="API da Academia",
    description="Sistema de gerenciamento de alunos, check-ins e tarefas assíncronas com RabbitMQ.",
    version="1.0.0",
    contact={
        "name": "Equipe de Desenvolvimento",
        "email": "contato@academia.com"
    }
)

# Inclui os módulos de rotas
app.include_router(alunos.router, prefix="/aluno", tags=["Alunos"])
app.include_router(checkins.router, prefix="/checkin", tags=["Check-ins"])
app.include_router(checkouts.router, prefix="/checkout", tags=["Check-outs"])
app.include_router(tarefas.router, prefix="/tarefas", tags=["Tarefas"])

# Rota raiz opcional
@app.get("/", tags=["Status"])
def root():
    return {"mensagem": "API da Academia em funcionamento"}
