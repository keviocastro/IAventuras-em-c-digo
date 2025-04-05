from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.db.database import get_db
from app.models.aluno import Aluno, Checkin, Plano, ChurnProbability
from app.schemas.aluno import TopChurnRiskResponse, AlunoChurnResponse

router = APIRouter(prefix="/estatisticas", tags=["estatisticas"])


@router.get("/frequencia", response_model=Dict[str, Any])
def obter_frequencia_semanal(db: Session = Depends(get_db)):
    """
    Retorna a frequência de alunos nos últimos 7 dias.
    """
    try:
        # Data de hoje
        hoje = datetime.now().date()
        
        # Lista de dias da semana para o resultado
        dias = []
        frequencia = []
        
        # Para cada um dos últimos 7 dias
        for i in range(6, -1, -1):
            data = hoje - timedelta(days=i)
            dias.append(data.strftime("%d/%m"))
            
            # Contar check-ins neste dia
            count = db.query(func.count(Checkin.id)).filter(
                cast(Checkin.data_entrada, Date) == data
            ).scalar()
            
            frequencia.append(count)
        
        return {
            "dias": dias,
            "frequencia": frequencia,
            "total_periodo": sum(frequencia)
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter estatísticas de frequência: {str(e)}"
        )


@router.post("/frequencia", status_code=status.HTTP_200_OK)
def recalcular_frequencia_semanal(db: Session = Depends(get_db)):
    """
    Recalcula as estatísticas de frequência semanal.
    Neste caso, como os dados são calculados em tempo real, apenas retorna os dados atuais.
    """
    return obter_frequencia_semanal(db)


@router.get("/planos", response_model=Dict[str, Any])
def obter_distribuicao_planos(db: Session = Depends(get_db)):
    """
    Retorna a distribuição de alunos por plano.
    """
    try:
        # Obter todos os planos
        planos = db.query(Plano).all()
        
        # Inicializar o resultado
        resultado = {
            "planos": [],
            "quantidades": [],
            "total_alunos": 0
        }
        
        # Para cada plano, contar quantos alunos ativos o possuem
        for plano in planos:
            resultado["planos"].append(plano.nome)
            
            # Contar alunos ativos com este plano
            count = db.query(func.count(Aluno.id)).filter(
                Aluno.plano_id == plano.id,
                Aluno.ativo == 1
            ).scalar()
            
            resultado["quantidades"].append(count)
            resultado["total_alunos"] += count
        
        return resultado
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter estatísticas de planos: {str(e)}"
        )


@router.post("/planos", status_code=status.HTTP_200_OK)
def recalcular_distribuicao_planos(db: Session = Depends(get_db)):
    """
    Recalcula as estatísticas de distribuição de planos.
    Neste caso, como os dados são calculados em tempo real, apenas retorna os dados atuais.
    """
    return obter_distribuicao_planos(db)


@router.get("/churn/top-risco", response_model=TopChurnRiskResponse)
def obter_top_alunos_risco_churn(limit: Optional[int] = 10, db: Session = Depends(get_db)):
    """
    Retorna os alunos com maior probabilidade de churn.
    
    Args:
        limit: Número máximo de alunos a retornar (padrão: 10)
    """
    try:
        # Obter os alunos com maior probabilidade de churn
        resultados = db.query(
            Aluno.id.label("aluno_id"),
            Aluno.nome,
            Aluno.email,
            Aluno.ativo,
            Plano.nome.label("plano_nome"),
            ChurnProbability.probabilidade.label("probabilidade_churn"),
            func.max(Checkin.data_entrada).label("ultima_visita")
        ).join(
            ChurnProbability, Aluno.id == ChurnProbability.aluno_id
        ).outerjoin(
            Plano, Aluno.plano_id == Plano.id
        ).outerjoin(
            Checkin, Aluno.id == Checkin.aluno_id
        ).filter(
            Aluno.ativo == 1  # Apenas alunos ativos
        ).group_by(
            Aluno.id, Aluno.nome, Aluno.email, Aluno.ativo, Plano.nome, ChurnProbability.probabilidade
        ).order_by(
            ChurnProbability.probabilidade.desc()
        ).limit(limit).all()
        
        # Processar resultados
        alunos_risco = []
        for resultado in resultados:
            # Calcular dias desde a última visita
            dias_desde_ultima_visita = None
            if resultado.ultima_visita:
                dias_desde_ultima_visita = (datetime.now() - resultado.ultima_visita).days
            
            aluno_churn = AlunoChurnResponse(
                aluno_id=resultado.aluno_id,
                nome=resultado.nome,
                email=resultado.email,
                ativo=resultado.ativo,
                plano_nome=resultado.plano_nome,
                probabilidade_churn=resultado.probabilidade_churn,
                ultima_visita=resultado.ultima_visita,
                dias_desde_ultima_visita=dias_desde_ultima_visita
            )
            alunos_risco.append(aluno_churn)
        
        return TopChurnRiskResponse(alunos_risco=alunos_risco)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter alunos com maior risco de churn: {str(e)}"
        )


@router.get("/churn/top-risco-completo", response_model=TopChurnRiskResponse)
def obter_top_alunos_risco_churn_completo(limit: Optional[int] = 10, db: Session = Depends(get_db)):
    """
    Retorna os alunos com maior probabilidade de churn, incluindo informações completas de última visita e dias inativos.
    Este endpoint evita múltiplas requisições para obter dados de cada aluno individualmente.
    
    Args:
        limit: Número máximo de alunos a retornar (padrão: 10)
    """
    try:
        # Primeiro, pegar os IDs dos alunos com maiores probabilidades de churn
        alunos_ids_query = db.query(
            Aluno.id.label("aluno_id"),
            ChurnProbability.probabilidade.label("probabilidade_churn")
        ).join(
            ChurnProbability, Aluno.id == ChurnProbability.aluno_id
        ).filter(
            Aluno.ativo == 1  # Apenas alunos ativos
        ).order_by(
            ChurnProbability.probabilidade.desc()
        ).limit(limit)
        
        alunos_ids = [resultado.aluno_id for resultado in alunos_ids_query]
        
        if not alunos_ids:
            return TopChurnRiskResponse(alunos_risco=[])
        
        # Processar resultados
        alunos_risco = []
        
        # Para cada aluno na lista, buscar informações detalhadas
        for aluno_id in alunos_ids:
            # Buscar informações base do aluno
            aluno_info = db.query(
                Aluno.id.label("aluno_id"),
                Aluno.nome,
                Aluno.email,
                Aluno.ativo,
                Plano.nome.label("plano_nome"),
                ChurnProbability.probabilidade.label("probabilidade_churn")
            ).join(
                ChurnProbability, Aluno.id == ChurnProbability.aluno_id
            ).outerjoin(
                Plano, Aluno.plano_id == Plano.id
            ).filter(
                Aluno.id == aluno_id
            ).first()
            
            if not aluno_info:
                continue
            
            # Contar quantos checkins o aluno tem
            count_checkins = db.query(func.count(Checkin.id)).filter(
                Checkin.aluno_id == aluno_id
            ).scalar()
            
            # Buscar a última visita do aluno
            ultima_visita_query = db.query(
                Checkin.data_entrada
            ).filter(
                Checkin.aluno_id == aluno_id
            ).order_by(
                Checkin.data_entrada.desc()
            ).first()
            
            # Processar informações de última visita e dias inativos
            ultima_visita = None
            dias_desde_ultima_visita = None
            
            if ultima_visita_query:
                ultima_visita = ultima_visita_query[0]
                dias_desde_ultima_visita = (datetime.now() - ultima_visita).days
            
            # Criar objeto de resposta
            aluno_churn = AlunoChurnResponse(
                aluno_id=aluno_info.aluno_id,
                nome=aluno_info.nome,
                email=aluno_info.email,
                ativo=aluno_info.ativo,
                plano_nome=aluno_info.plano_nome,
                probabilidade_churn=aluno_info.probabilidade_churn,
                ultima_visita=ultima_visita,
                dias_desde_ultima_visita=dias_desde_ultima_visita
            )
            
            alunos_risco.append(aluno_churn)
        
        # Reordenar por probabilidade de churn (pode ter perdido a ordem original)
        alunos_risco.sort(key=lambda x: x.probabilidade_churn, reverse=True)
        
        return TopChurnRiskResponse(alunos_risco=alunos_risco)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter alunos com maior risco de churn completo: {str(e)}"
        ) 