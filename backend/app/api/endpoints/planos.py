from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.models.aluno import Plano
from app.schemas.aluno import PlanoCreate, PlanoResponse
from app.services.plano_service import PlanoService

router = APIRouter(prefix="/plano", tags=["planos"])


@router.post("/", response_model=PlanoResponse, status_code=status.HTTP_201_CREATED)
def criar_plano(plano: PlanoCreate, db: Session = Depends(get_db)):
    """
    Cria um novo plano de academia.
    """
    return PlanoService(db).criar_plano(plano)


@router.get("/", response_model=List[PlanoResponse])
def listar_planos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retorna a lista de planos disponíveis.
    """
    return PlanoService(db).listar_planos(skip=skip, limit=limit)


@router.get("/{plano_id}", response_model=PlanoResponse)
def obter_plano(plano_id: int, db: Session = Depends(get_db)):
    """
    Retorna os detalhes de um plano específico.
    """
    plano = PlanoService(db).obter_plano_por_id(plano_id)
    if not plano:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plano não encontrado"
        )
    return plano


@router.put("/{plano_id}", response_model=PlanoResponse)
def atualizar_plano(plano_id: int, plano: PlanoCreate, db: Session = Depends(get_db)):
    """
    Atualiza as informações de um plano existente.
    """
    plano_atual = PlanoService(db).obter_plano_por_id(plano_id)
    if not plano_atual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plano não encontrado"
        )
    return PlanoService(db).atualizar_plano(plano_id, plano)


@router.delete("/{plano_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_plano(plano_id: int, db: Session = Depends(get_db)):
    """
    Remove um plano do sistema.
    """
    plano = PlanoService(db).obter_plano_por_id(plano_id)
    if not plano:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plano não encontrado"
        )
    
    # Verificar se existem alunos usando este plano
    alunos_com_plano = db.query(Plano).filter(Plano.id == plano_id).first().alunos
    if alunos_com_plano and len(alunos_com_plano) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não é possível remover este plano pois existem {len(alunos_com_plano)} alunos associados a ele"
        )
    
    PlanoService(db).remover_plano(plano_id)
    return None 