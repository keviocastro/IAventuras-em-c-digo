from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.models.aluno import Aluno
from app.models.usuario import Usuario
from app.schemas.aluno import AlunoCreate, AlunoResponse, CheckinCreate, FrequenciaResponse, RiscoChurnResponse
from app.services.aluno_service import AlunoService
from app.api.dependencies import get_current_active_user, get_current_admin_user

router = APIRouter(prefix="/aluno", tags=["alunos"])


@router.post("/registro", response_model=AlunoResponse, status_code=status.HTTP_201_CREATED)
def criar_aluno(
    aluno: AlunoCreate, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Registrar um novo aluno na academia.
    """
    db_aluno = AlunoService(db).criar_aluno(aluno)
    return db_aluno


@router.get("/", response_model=List[AlunoResponse])
def listar_alunos(
    skip: int = 0, 
    limit: int = 100, 
    nome: Optional[str] = None, 
    email: Optional[str] = None,
    ativo: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Retorna a lista de todos os alunos, com filtros opcionais.
    """
    return AlunoService(db).listar_alunos(skip=skip, limit=limit, nome=nome, email=email, ativo=ativo)


@router.get("/{aluno_id}", response_model=AlunoResponse)
def obter_aluno(
    aluno_id: int, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Retorna os detalhes de um aluno específico.
    """
    aluno = AlunoService(db).obter_aluno_por_id(aluno_id)
    if not aluno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aluno não encontrado"
        )
    return aluno


@router.put("/{aluno_id}", response_model=AlunoResponse)
def atualizar_aluno(
    aluno_id: int, 
    aluno: AlunoCreate, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Atualiza as informações de um aluno existente.
    """
    db_aluno = AlunoService(db).obter_aluno_por_id(aluno_id)
    if not db_aluno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aluno não encontrado"
        )
    return AlunoService(db).atualizar_aluno(aluno_id, aluno)


@router.patch("/{aluno_id}/ativar", response_model=AlunoResponse)
def ativar_aluno(
    aluno_id: int, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_admin_user)  # Apenas admins podem ativar
):
    """
    Ativa um aluno (define status como ativo).
    """
    db_aluno = AlunoService(db).obter_aluno_por_id(aluno_id)
    if not db_aluno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aluno não encontrado"
        )
    return AlunoService(db).atualizar_status_aluno(aluno_id, ativo=1)


@router.patch("/{aluno_id}/desativar", response_model=AlunoResponse)
def desativar_aluno(
    aluno_id: int, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_admin_user)  # Apenas admins podem desativar
):
    """
    Desativa um aluno (define status como inativo).
    """
    db_aluno = AlunoService(db).obter_aluno_por_id(aluno_id)
    if not db_aluno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aluno não encontrado"
        )
    return AlunoService(db).atualizar_status_aluno(aluno_id, ativo=0)


@router.post("/checkin", status_code=status.HTTP_201_CREATED)
def registrar_checkin(
    checkin: CheckinCreate, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Registrar entrada ou saída do aluno na academia.
    """
    try:
        return AlunoService(db).registrar_checkin(checkin)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{aluno_id}/frequencia", response_model=FrequenciaResponse)
def obter_frequencia(
    aluno_id: int, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Obter histórico de frequência do aluno.
    """
    aluno = AlunoService(db).obter_aluno_por_id(aluno_id)
    if not aluno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aluno não encontrado"
        )
    
    try:
        return AlunoService(db).obter_frequencia(aluno_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{aluno_id}/risco-churn", response_model=RiscoChurnResponse)
def obter_risco_churn(
    aluno_id: int, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Obter probabilidade de desistência do aluno.
    """
    aluno = AlunoService(db).obter_aluno_por_id(aluno_id)
    if not aluno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aluno não encontrado"
        )
    
    try:
        return AlunoService(db).calcular_risco_churn(aluno_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 