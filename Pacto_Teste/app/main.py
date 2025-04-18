from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Annotated
import app.models as models
from app.database import engine, SessionLocal 
from sqlalchemy.orm import Session
from datetime import date, timedelta, time
from app.queue_manager import QueueManager


app = FastAPI()
models.Base.metadata.create_all(bind=engine)

class AlunoBase(BaseModel):
    nome: str
    plano: str

class frequenciaBase(BaseModel):
    aluno_id: int
    data: str
    horario_checkin: time
    horario_checkout: time

class planoBase(BaseModel):
    nome: str
    valor: int
    duracao: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]


@app.post("/aluno/registro") # registro de alunos
async def create_aluno(aluno: AlunoBase, db: db_dependency):
    db_aluno = models.Aluno(nome=aluno.nome, plano=aluno.plano)
    db.add(db_aluno)
    db.commit()
    db.refresh(db_aluno)

@app.post("/aluno/checkin") # check-in de alunos
async def create_checkin(checkin: frequenciaBase, db: db_dependency):
    aluno = db.query(models.Aluno).filter(models.Aluno.id == checkin.aluno_id).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    try:
        # Envia mensagem para o RabbitMQ para processar o check-in
        queue_manager = QueueManager()
        queue_manager.publish_checkin(
            checkin.aluno_id,
            checkin.data,
            checkin.horario_checkin.isoformat(),
            checkin.horario_checkout.isoformat()
        )

        # Envia mensagem para atualizar o churn
        queue_manager.publish_churn_update()
        queue_manager.close()

        return {"message": "Check-in enviado para processamento e atualização de churn via RabbitMQ."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alunos/{id}/frequencia")
async def get_frequencia(id: int, db: db_dependency):
    aluno = db.query(models.Aluno).filter(models.Aluno.id == id).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    frequencias = db.query(models.checkins).filter(models.checkins.aluno_id == id).all()
    return frequencias

@app.get("/aluno/{id}/risco-churn")
async def get_risco_churn(id: int, db: db_dependency):
    aluno = db.query(models.Aluno).filter(models.Aluno.id == id).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    return {"risco_churn": aluno.risco_churn}