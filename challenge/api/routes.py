from fastapi import FastAPI
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Corrigir os imports - separar database de entities
from challenge.models.database import get_db, Base, engine
from challenge.models.entities import Plano, Aluno, CheckIn

from challenge.models.schemas import (
    PlanoCreate,
    PlanoResponse,
    AlunoCreate,
    AlunoResponse,
    CheckInCreate,
    CheckInResponse,
)

# Criar tabelas no banco se não existirem
Base.metadata.create_all(bind=engine)

app = FastAPI()
router = APIRouter()


@router.get("/")
def read_root():
    return {"message": "Hello World!"}


@router.get("/alunos", response_model=list[AlunoResponse])
def listar_alunos(db: Session = Depends(get_db)):
    """Lista todos os alunos cadastrados"""
    return db.query(Aluno).all()


app.include_router(router)
