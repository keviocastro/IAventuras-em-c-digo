from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel

from app.db.database import get_db
from app.models.aluno import Checkin
from app.schemas.aluno import CheckinResponse, CheckinCreate
from app.services.checkin_service import CheckinService

# Importar produtor RabbitMQ
from app.queue.producers import enviar_checkins_em_massa

router = APIRouter(prefix="/checkin", tags=["checkins"])


@router.get("/", response_model=List[CheckinResponse])
def listar_checkins(
    skip: int = 0, 
    limit: int = 100,
    aluno_id: Optional[int] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Retorna a lista de todos os checkins, com filtros opcionais.
    """
    return CheckinService(db).listar_checkins(
        skip=skip, 
        limit=limit, 
        aluno_id=aluno_id, 
        data_inicio=data_inicio, 
        data_fim=data_fim
    )


@router.get("/ativos", response_model=List[CheckinResponse])
def listar_checkins_ativos(db: Session = Depends(get_db)):
    """
    Retorna a lista de checkins ativos (alunos que estão na academia).
    """
    return CheckinService(db).listar_checkins_ativos()


@router.post("/fechar-todos", status_code=status.HTTP_200_OK)
def fechar_todos_checkins_ativos(db: Session = Depends(get_db)):
    """
    Fecha todos os check-ins ativos, registrando a saída para todos 
    os alunos que têm check-in de entrada mas não têm de saída.
    """
    try:
        # Obter todos os check-ins ativos
        checkins_ativos = CheckinService(db).listar_checkins_ativos()
        total = len(checkins_ativos)
        
        if total == 0:
            return {"message": "Não há check-ins ativos para fechar."}
        
        # Registrar saída para cada um
        agora = datetime.now()
        fechados = 0
        
        for checkin in checkins_ativos:
            try:
                # Calcular duração em minutos
                duracao = (agora - checkin.data_entrada).total_seconds() / 60
                
                # Atualizar o check-in
                checkin.data_saida = agora
                checkin.duracao_minutos = int(duracao)
                
                # Incrementar contador
                fechados += 1
            except Exception as e:
                # Logar erro mas continuar com os próximos
                db.rollback()
                print(f"Erro ao fechar check-in {checkin.id}: {str(e)}")
        
        # Commit das alterações
        db.commit()
        
        return {
            "message": f"Check-ins fechados com sucesso: {fechados} de {total}",
            "total_fechados": fechados,
            "total_checkins": total
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao fechar check-ins: {str(e)}"
        )


@router.get("/{checkin_id}", response_model=CheckinResponse)
def obter_checkin(checkin_id: int, db: Session = Depends(get_db)):
    """
    Retorna os detalhes de um checkin específico.
    """
    checkin = CheckinService(db).obter_checkin_por_id(checkin_id)
    if not checkin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checkin não encontrado"
        )
    return checkin


@router.delete("/{checkin_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_checkin(checkin_id: int, db: Session = Depends(get_db)):
    """
    Remove um checkin do sistema.
    """
    checkin = CheckinService(db).obter_checkin_por_id(checkin_id)
    if not checkin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checkin não encontrado"
        )
    
    CheckinService(db).remover_checkin(checkin_id)
    return None


class CheckinBatchRequest(BaseModel):
    checkins: List[Dict[str, Any]]
    timestamp: Optional[str] = None


@router.post("/batch", status_code=status.HTTP_202_ACCEPTED)
def registrar_checkins_batch(payload: CheckinBatchRequest = Body(...)):
    """
    Registra múltiplos checkins de forma assíncrona através do RabbitMQ.
    
    Este endpoint envia os dados para uma fila do RabbitMQ, que serão processados
    por um worker em segundo plano. Isso permite processar grandes volumes de
    checkins sem bloquear a resposta da API.
    """
    # Verificar se há checkins na requisição
    if not payload.checkins:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum checkin fornecido no corpo da requisição"
        )
    
    # Enviar para a fila do RabbitMQ
    sucesso = enviar_checkins_em_massa(payload.dict()["checkins"])
    
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao processar checkins em lote. Tente novamente mais tarde."
        )
    
    return {"message": f"{len(payload.checkins)} checkins enviados para processamento em segundo plano"} 