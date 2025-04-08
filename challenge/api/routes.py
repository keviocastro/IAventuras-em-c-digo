from datetime import datetime
from http import HTTPStatus
from fastapi import FastAPI
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

# Corrigir os imports - separar database de entities
from models.database import get_db, Base, engine
from models.entities import Plano, Aluno, CheckIn

from models.schemas import (
    PlanoCreate,
    PlanoResponse,
    AlunoCreate,
    AlunoResponse,
    CheckInCreate,
    CheckInResponse,
    CheckInBatchCreate,
    CheckInUpdate,
)

from rabbitmq.producers.base import (
    publicar_checkin_ou_checkout,
    publicar_checkins_em_massa,
    solicitar_relatorio_diario,
    solicitar_atualizacao_modelo_churn,
)

# Criar tabelas no banco se não existirem
Base.metadata.create_all(bind=engine)

app = FastAPI()
router = APIRouter()


@router.get("/")
def read_root():
    return {"message": "Hello World!"}


# COMPLETAR AS ROTAS PARA O CRUD


# Registrar um novo aluno
@router.post(
    "/aluno/registro",
    response_model=AlunoResponse,
    status_code=HTTPStatus.CREATED,
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


# Registrar entrada do aluno na academia
@router.post(
    "/aluno/checkin",
    response_model=CheckInResponse,
    status_code=HTTPStatus.CREATED,
)
def criar_checkin(
    checkin: CheckInCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Cadastra um novo check-in"""
    # Verificar se o aluno existe
    aluno = db.query(Aluno).filter(Aluno.id == checkin.aluno_id).first()
    if not aluno:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Aluno não encontrado"
        )

    # Criar objeto CheckIn a partir dos dados recebidos
    db_checkin = CheckIn(**checkin.model_dump())
    db_checkin.data_entrada = datetime.now()

    # Adicionar ao banco e commit
    db.add(db_checkin)
    db.commit()
    db.refresh(db_checkin)

    # Publicar evento no RabbitMQ em segundo plano
    background_tasks.add_task(
        publicar_checkin_ou_checkout,
        aluno_id=db_checkin.aluno_id,
        timestamp=db_checkin.data_entrada.isoformat(),
        entrada=True,
    )

    return db_checkin


# Atualizar checkin com a saída do aluno da academia
@router.put(
    "/aluno/checkout",
    response_model=CheckInResponse,
    status_code=HTTPStatus.OK,
)
def atualizar_checkout(
    checkout_data: CheckInUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Atualiza o check-in com a saída do aluno"""
    # Verificar se o aluno existe
    aluno = db.query(Aluno).filter(Aluno.id == checkout_data.aluno_id).first()
    if not aluno:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Aluno não encontrado"
        )

    # Obter o último check-in do aluno
    ultimo_checkin = (
        db.query(CheckIn)
        .filter(CheckIn.aluno_id == checkout_data.aluno_id)
        .order_by(CheckIn.data_entrada.desc())
        .first()
    )

    if not ultimo_checkin or ultimo_checkin.duracao_treino:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Nenhum check-in em aberto encontrado para o aluno",
        )

    ultimo_checkin.duracao_treino = (
        checkout_data.duracao_treino
        or (datetime.now() - ultimo_checkin.data_entrada).total_seconds() / 60
    )

    db.commit()
    db.refresh(ultimo_checkin)

    # Publicar evento no RabbitMQ em segundo plano
    background_tasks.add_task(
        publicar_checkin_ou_checkout,
        aluno_id=checkout_data.aluno_id,
        timestamp=datetime.now().isoformat(),
        entrada=False,
    )

    return ultimo_checkin


# Obter histórico de frequência
@router.get("/aluno/{id}/frequencia")
def listar_frequencia_aluno(id: int, db: Session = Depends(get_db)):
    """Lista a frequência do aluno"""
    # Verificar se o aluno existe
    aluno = db.query(Aluno).filter(Aluno.id == id).first()
    if not aluno:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Aluno não encontrado"
        )

    # Obter todos os check-ins do aluno
    checkins = db.query(CheckIn).filter(CheckIn.aluno_id == id).all()

    return checkins


# TO DO: Obter probabilidade de desistência


# Listar todos os alunos
@router.get("/alunos", response_model=list[AlunoResponse])
def listar_alunos(db: Session = Depends(get_db)):
    """Lista todos os alunos cadastrados"""
    return db.query(Aluno).all()


# Listar todos os planos
@router.get("/planos", response_model=list[PlanoResponse])
def listar_planos(db: Session = Depends(get_db)):
    """Lista todos os planos cadastrados"""
    return db.query(Plano).all()


# Registrar um novo plano
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


# Listar todos os check-ins
@router.get("/checkins", response_model=list[CheckInResponse])
def listar_checkins(db: Session = Depends(get_db)):
    """Lista todos os check-ins cadastrados"""
    return db.query(CheckIn).all()


# Rota para processar checkins em massa
@router.post("/alunos/checkins/batch", status_code=HTTPStatus.ACCEPTED)
def processar_checkins_em_massa(
    checkins: list[CheckInBatchCreate], background_tasks: BackgroundTasks
):
    """Envia um lote de check-ins para processamento assíncrono"""
    if not checkins:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Lista de check-ins vazia",
        )

    # Processar os check-ins em segundo plano
    formatted_checkins = []
    for checkin in checkins:
        formatted_checkins.append(
            {
                "aluno_id": checkin.aluno_id,
                "timestamp": checkin.timestamp or datetime.now().isoformat(),
                "tipo": "entrada" if checkin.entrada else "saida",
            }
        )

    background_tasks.add_task(
        publicar_checkins_em_massa, checkins=formatted_checkins
    )

    return {
        "message": f"{len(checkins)} check-ins enviados para processamento"
    }


# Rota para solicitar geração de relatório diário
@router.post("/relatorios/diario", status_code=HTTPStatus.ACCEPTED)
def gerar_relatorio_diario(
    background_tasks: BackgroundTasks, data: str = None
):
    """Solicita a geração de um relatório diário de frequência"""
    background_tasks.add_task(solicitar_relatorio_diario, data=data)

    return {"message": "Solicitação de relatório diário enviada"}


# Rota para solicitar atualização do modelo de churn
@router.post("/modelo/churn/atualizar", status_code=HTTPStatus.ACCEPTED)
def atualizar_modelo_churn(background_tasks: BackgroundTasks):
    """Solicita a atualização do modelo de previsão de churn"""
    background_tasks.add_task(solicitar_atualizacao_modelo_churn)

    return {"message": "Solicitação de atualização do modelo de churn enviada"}


app.include_router(router)
