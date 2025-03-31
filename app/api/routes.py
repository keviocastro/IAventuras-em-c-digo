from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models import Aluno, Checkin
from app.models.database import SessionLocal
from pydantic import BaseModel
from datetime import datetime

# Criar o router para as rotas de alunos e check-ins
router = APIRouter()

# Pydantic model para a criação de aluno
class AlunoCreate(BaseModel):
    nome: str
    data_nascimento: str
    genero: str
    email: str
    plano_id: int
    data_matricula: str
    matricula_ativa: bool
    data_cancelamento: str = None  # Pode ser opcional

# Pydantic model para a criação de check-in
class CheckinCreate(BaseModel):
    aluno_id: int  # ID do aluno que está fazendo o check-in

# Função para obter a sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Endpoint para cadastrar um novo aluno
@router.post("/alunos")
def create_aluno(aluno: AlunoCreate, db: Session = Depends(get_db)):
    db_aluno = db.query(Aluno).filter(Aluno.email == aluno.email).first()
    if db_aluno:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    novo_aluno = Aluno(
        nome=aluno.nome,
        data_nascimento=datetime.strptime(aluno.data_nascimento, "%Y-%m-%d").date(),
        genero=aluno.genero,
        email=aluno.email,
        plano_id=aluno.plano_id,
        data_matricula=datetime.strptime(aluno.data_matricula, "%Y-%m-%d").date(),
        matricula_ativa=aluno.matricula_ativa,
        data_cancelamento=datetime.strptime(aluno.data_cancelamento, "%Y-%m-%d").date() if aluno.data_cancelamento else None
    )
    
    db.add(novo_aluno)
    db.commit()
    db.refresh(novo_aluno)
    return novo_aluno

# Endpoint para visualizar todos os alunos
@router.get("/alunos")
def get_alunos(db: Session = Depends(get_db)):
    alunos = db.query(Aluno).all()
    return alunos

# ------------------ Check-in ------------------

# Endpoint para cadastrar um novo check-in
@router.post("/checkins")
def create_checkin(checkin: CheckinCreate, db: Session = Depends(get_db)):
    # Verificar se o aluno existe
    aluno = db.query(Aluno).filter(Aluno.matricula == checkin.aluno_id).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    # Obter a data e hora atuais
    data_atual = datetime.utcnow()

    # Verificar as regras de matrícula antes de permitir o check-in
    if not aluno.matricula_ativa:
        if aluno.data_cancelamento is None or data_atual.date() > aluno.data_cancelamento:
            raise HTTPException(status_code=400, detail="Matrícula inativa. Check-in não permitido.")

    # Criar o check-in
    novo_checkin = Checkin(
    aluno_id=checkin.aluno_id,  
    data_hora_entrada=datetime.utcnow()  # Aqui usamos o nome correto
)

    db.add(novo_checkin)
    db.commit()
    db.refresh(novo_checkin)
    
    return novo_checkin

# Endpoint para visualizar todos os check-ins
@router.get("/checkins")
def list_checkins(db: Session = Depends(get_db)):
    return db.query(Checkin).all()

# Endpoint para visualizar os check-ins de um aluno específico
@router.get("/checkins/{aluno_id}")
def list_checkins_by_aluno(aluno_id: int, db: Session = Depends(get_db)):
    checkins = db.query(Checkin).filter(Checkin.aluno_id == aluno_id).all()
    if not checkins:
        raise HTTPException(status_code=404, detail="Nenhum check-in encontrado para este aluno")
    
    return checkins
