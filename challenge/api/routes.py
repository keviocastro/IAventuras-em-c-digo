from http import HTTPStatus
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


# ---------- Rotas de Alunos -----------


@router.get("/alunos", response_model=list[AlunoResponse])
def listar_alunos(db: Session = Depends(get_db)):
    """Lista todos os alunos cadastrados"""
    return db.query(Aluno).all()


@router.post(
    "/alunos", response_model=AlunoResponse, status_code=HTTPStatus.CREATED
)
def criar_aluno(aluno: AlunoCreate, db: Session = Depends(get_db)):
    """Cadastra um novo aluno"""
    # Verificar se o email já existe
    if db.query(Aluno).filter(Aluno.email == aluno.email).first():
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Email já cadastrado"
        )

    # Verificar se o plano existe
    plano = db.query(Plano).filter(Plano.id == aluno.plano_id).first()
    if not plano:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Plano não encontrado"
        )

    # Criar objeto Aluno a partir dos dados recebidos
    db_aluno = Aluno(**aluno.model_dump())

    # Adicionar ao banco e commit
    db.add(db_aluno)
    db.commit()
    db.refresh(db_aluno)

    return db_aluno


# ---------- Rotas de Planos -----------


@router.get("/planos", response_model=list[PlanoResponse])
def listar_planos(db: Session = Depends(get_db)):
    """Lista todos os planos cadastrados"""
    return db.query(Plano).all()


@router.post(
    "/planos", response_model=PlanoResponse, status_code=HTTPStatus.CREATED
)
def criar_plano(plano: PlanoCreate, db: Session = Depends(get_db)):
    """Cadastra um novo plano"""
    # Verificar se o nome já existe
    if db.query(Plano).filter(Plano.nome == plano.nome).first():
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Nome do plano já cadastrado",
        )

    # Criar objeto Plano a partir dos dados recebidos
    db_plano = Plano(**plano.model_dump())

    # Adicionar ao banco e commit
    db.add(db_plano)
    db.commit()
    db.refresh(db_plano)

    return db_plano


# ---------- Rotas de CheckIns -----------


@router.get("/checkins", response_model=list[CheckInResponse])
def listar_checkins(db: Session = Depends(get_db)):
    """Lista todos os check-ins cadastrados"""
    return db.query(CheckIn).all()


@router.post(
    "/checkins", response_model=CheckInResponse, status_code=HTTPStatus.CREATED
)
def criar_checkin(checkin: CheckInCreate, db: Session = Depends(get_db)):
    """Cadastra um novo check-in"""
    # Verificar se o aluno existe
    aluno = db.query(Aluno).filter(Aluno.id == checkin.aluno_id).first()
    if not aluno:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Aluno não encontrado"
        )

    # Criar objeto CheckIn a partir dos dados recebidos
    db_checkin = CheckIn(**checkin.model_dump())

    # Adicionar ao banco e commit
    db.add(db_checkin)
    db.commit()
    db.refresh(db_checkin)

    return db_checkin


app.include_router(router)
