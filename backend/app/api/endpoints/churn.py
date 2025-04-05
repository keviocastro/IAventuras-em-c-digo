from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
import joblib
import numpy as np
import pandas as pd
from datetime import datetime

from app.db.database import get_db
from app.models.aluno import Aluno, Checkin, Plano, ModeloChurnEstatisticas, ChurnProbability
from app.models.usuario import Usuario
from app.schemas.aluno import RiscoChurnResponse
from app.queue.producers import solicitar_atualizacao_modelo, solicitar_calculo_probabilidades_churn
from app.services.aluno_service import AlunoService
from app.api.dependencies import get_current_admin_user, get_current_active_user

# Definir caminho para os modelos
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "modelo_churn.pkl")
FEATURE_INFO_PATH = os.path.join(MODEL_DIR, "feature_info.pkl")

router = APIRouter(prefix="/churn", tags=["churn"])


@router.post("/treinar-modelo", status_code=status.HTTP_202_ACCEPTED)
def treinar_modelo(current_user: Usuario = Depends(get_current_admin_user)):
    """
    Solicita o treinamento assíncrono do modelo de previsão de churn usando RabbitMQ.
    Os dados serão processados em segundo plano e o modelo será salvo.
    Requer autenticação de administrador.
    """
    # Enviar solicitação para a fila do RabbitMQ
    sucesso = solicitar_atualizacao_modelo()
    
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao solicitar treinamento do modelo. Verifique o serviço RabbitMQ."
        )
    
    return {"message": "Solicitação de treinamento do modelo enviada com sucesso. O processo será executado em segundo plano."}


@router.post("/calcular-probabilidades", status_code=status.HTTP_202_ACCEPTED)
def calcular_probabilidades_todos(current_user: Usuario = Depends(get_current_admin_user)):
    """
    Solicita o cálculo assíncrono das probabilidades de churn para todos os alunos usando RabbitMQ.
    Os resultados serão salvos no banco de dados.
    Requer autenticação de administrador.
    """
    # Enviar solicitação para a fila do RabbitMQ
    sucesso = solicitar_calculo_probabilidades_churn()
    
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao solicitar cálculo de probabilidades. Verifique o serviço RabbitMQ."
        )
    
    return {"message": "Solicitação de cálculo de probabilidades enviada com sucesso. O processamento será executado em segundo plano."}


@router.get("/aluno/{aluno_id}", response_model=RiscoChurnResponse)
def calcular_probabilidade_aluno(
    aluno_id: int = Path(..., gt=0), 
    recalcular: bool = False, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Calcula a probabilidade de churn para um aluno específico.
    Se recalcular=False (padrão), primeiro tenta buscar do banco de dados.
    Se recalcular=True ou se não existir no banco, calcula usando o modelo.
    Requer autenticação.
    """
    # Verificar se o aluno existe
    aluno = db.query(Aluno).filter(Aluno.id == aluno_id).first()
    if not aluno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aluno não encontrado"
        )
    
    # Verificar se já existe probabilidade calculada no banco de dados e se não foi solicitado recálculo
    if not recalcular:
        churn_prob = db.query(ChurnProbability).filter(ChurnProbability.aluno_id == aluno_id).first()
        
        if churn_prob:
            # Obter informações sobre a última visita (para dados sempre atualizados)
            ultima_visita = db.query(Checkin.data_entrada).filter(
                Checkin.aluno_id == aluno_id
            ).order_by(Checkin.data_entrada.desc()).first()
            
            # Calcular dias desde a última visita
            dias_desde_ultima_visita = None
            if ultima_visita:
                dias_desde_ultima_visita = (datetime.now() - ultima_visita[0]).days
            
            # Transformar string de fatores de risco em lista
            fatores_risco = churn_prob.fatores_risco.split(",") if churn_prob.fatores_risco else []
            
            # Gerar recomendações com base nos fatores de risco
            recomendacoes = gerar_recomendacoes(fatores_risco)
            
            # Retornar dados do banco
            return RiscoChurnResponse(
                aluno_id=aluno_id,
                probabilidade_churn=float(churn_prob.probabilidade),
                fatores_risco=fatores_risco,
                ultima_visita=ultima_visita[0] if ultima_visita else None,
                dias_desde_ultima_visita=dias_desde_ultima_visita,
                recomendacoes=recomendacoes
            )
        else:
            # Se não existe no banco e não foi solicitado recálculo,
            # usar método simples do AlunoService como fallback
            try:
                aluno_service = AlunoService(db)
                return aluno_service.calcular_risco_churn(aluno_id)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao calcular risco de churn via método simplificado: {str(e)}"
                )
    
    # Se recalcular=True, verifica se o modelo existe
    if not os.path.exists(MODEL_PATH) or not os.path.exists(FEATURE_INFO_PATH):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Modelo de previsão não encontrado. Execute o treinamento primeiro."
        )
    
    try:
        # Carregar o modelo e informações das features
        modelo = joblib.load(MODEL_PATH)
        feature_info = joblib.load(FEATURE_INFO_PATH)
        
        # Extrair as características do aluno para previsão
        features = extrair_features_aluno(aluno_id, db)
        
        # Preparar os dados no formato esperado pelo modelo
        X = pd.DataFrame([features])
        
        # Previsão de probabilidade
        probabilidade = modelo.predict_proba(X)[0, 1]  # Probabilidade da classe 1 (churn)
        
        # Identificar fatores de risco
        fatores_risco = identificar_fatores_risco(features)
        
        # Gerar recomendações com base nos fatores de risco
        recomendacoes = gerar_recomendacoes(fatores_risco)
        
        # Obter informações sobre a última visita
        ultima_visita = db.query(Checkin.data_entrada).filter(
            Checkin.aluno_id == aluno_id
        ).order_by(Checkin.data_entrada.desc()).first()
        
        # Calcular dias desde a última visita
        dias_desde_ultima_visita = None
        if ultima_visita:
            dias_desde_ultima_visita = (datetime.now() - ultima_visita[0]).days
        
        # Se recalcular=True, atualizar o banco de dados
        churn_prob = db.query(ChurnProbability).filter(ChurnProbability.aluno_id == aluno_id).first()
        
        if churn_prob:
            # Atualizar registro existente
            churn_prob.probabilidade = float(probabilidade)
            churn_prob.fatores_risco = ",".join(fatores_risco)
            churn_prob.ultima_atualizacao = datetime.now()
        else:
            # Criar novo registro
            churn_prob = ChurnProbability(
                aluno_id=aluno_id,
                probabilidade=float(probabilidade),
                fatores_risco=",".join(fatores_risco)
            )
            db.add(churn_prob)
        
        db.commit()
        
        # Retornar resultado
        return RiscoChurnResponse(
            aluno_id=aluno_id,
            probabilidade_churn=float(probabilidade),
            fatores_risco=fatores_risco,
            ultima_visita=ultima_visita[0] if ultima_visita else None,
            dias_desde_ultima_visita=dias_desde_ultima_visita,
            recomendacoes=recomendacoes
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao calcular probabilidade de churn: {str(e)}"
        )


def extrair_features_aluno(aluno_id: int, db: Session) -> Dict[str, Any]:
    """
    Extrai as características relevantes de um aluno para previsão de churn.
    """
    # Obter informações básicas do aluno
    aluno = db.query(Aluno).filter(Aluno.id == aluno_id).first()
    
    # Obter checkins do aluno
    checkins = db.query(Checkin).filter(Checkin.aluno_id == aluno_id).all()
    
    # Calcular estatísticas
    total_checkins = len(checkins)
    
    # Última visita e dias desde a última visita
    ultima_visita = db.query(Checkin.data_entrada).filter(
        Checkin.aluno_id == aluno_id
    ).order_by(Checkin.data_entrada.desc()).first()
    
    dias_desde_ultima_visita = 365  # Valor padrão alto
    if ultima_visita:
        dias_desde_ultima_visita = (datetime.now() - ultima_visita[0]).days
    
    # Duração média das visitas
    duracoes = [c.duracao_minutos for c in checkins if c.duracao_minutos is not None]
    duracao_media = sum(duracoes) / len(duracoes) if duracoes else 0
    
    # Média de visitas semanais
    if total_checkins > 0 and checkins:
        primeira_visita = min(c.data_entrada for c in checkins)
        semanas = max(1, (datetime.now() - primeira_visita).days / 7)
        media_visitas_semanais = total_checkins / semanas
    else:
        media_visitas_semanais = 0
    
    # Plano do aluno
    plano = db.query(Plano).filter(Plano.id == aluno.plano_id).first()
    
    # Criar dicionário de features
    features = {
        'total_checkins': total_checkins,
        'dias_desde_ultima_visita': dias_desde_ultima_visita,
        'duracao_media': duracao_media,
        'media_visitas_semanais': media_visitas_semanais,
        'plano_id': aluno.plano_id,
        'plano_nome': plano.nome if plano else "Desconhecido",
        'valor_mensal': plano.valor_mensal if plano else 0
    }
    
    return features


def identificar_fatores_risco(features: Dict[str, Any]) -> List[str]:
    """
    Identifica os fatores de risco com base nas características do aluno.
    """
    fatores_risco = []
    
    # Avaliar fatores de risco
    if features['dias_desde_ultima_visita'] > 30:
        fatores_risco.append(f"Inatividade há {features['dias_desde_ultima_visita']} dias")
    
    if features['media_visitas_semanais'] < 1:
        fatores_risco.append("Frequência menor que 1 visita por semana")
    
    if features['duracao_media'] < 30:
        fatores_risco.append(f"Duração média das visitas de apenas {int(features['duracao_media'])} minutos")
    
    if features['total_checkins'] < 5:
        fatores_risco.append("Poucas visitas à academia")
    
    return fatores_risco


def gerar_recomendacoes(fatores_risco: List[str]) -> List[str]:
    """
    Gera recomendações com base nos fatores de risco identificados.
    """
    recomendacoes = []
    
    for fator in fatores_risco:
        if "Inatividade" in fator:
            recomendacoes.append("Entrar em contato com o aluno para incentivar o retorno")
            recomendacoes.append("Oferecer uma aula experimental gratuita com personal trainer")
        
        if "Frequência menor" in fator:
            recomendacoes.append("Sugerir horários alternativos que se encaixem melhor na rotina")
            recomendacoes.append("Enviar lembretes personalizados sobre aulas e atividades")
        
        if "Duração média" in fator:
            recomendacoes.append("Recomendar séries de exercícios mais completas")
            recomendacoes.append("Oferecer avaliação física gratuita para ajuste da rotina de treino")
        
        if "Poucas visitas" in fator:
            recomendacoes.append("Oferecer desconto em renovação para incentivar continuidade")
            recomendacoes.append("Convidar para eventos sociais da academia")
    
    # Remover recomendações duplicadas
    return list(set(recomendacoes))


@router.get("/modelos", status_code=status.HTTP_200_OK)
def listar_modelos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Lista todos os modelos de previsão registrados no sistema.
    Requer autenticação.
    """
    try:
        # Obter todos os modelos ordenados por data de criação (mais recente primeiro)
        modelos = db.query(ModeloChurnEstatisticas).order_by(
            ModeloChurnEstatisticas.data_criacao.desc()
        ).all()
        
        # Converter para formato JSON serializável
        resultado = {
            "modelos": [
                {
                    "id": m.id,
                    "data_criacao": m.data_criacao.isoformat(),
                    "total_amostras": m.total_amostras,
                    "qtd_ativos": m.qtd_ativos,
                    "qtd_inativos": m.qtd_inativos,
                    "acuracia": m.acuracia,
                    "precisao": m.precisao,
                    "recall": m.recall,
                    "f1_score": m.f1_score,
                    "auc": m.auc,
                    "versao_modelo": m.versao_modelo,
                    "descricao": m.descricao
                }
                for m in modelos
            ]
        }
        
        return resultado
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar modelos de churn: {str(e)}"
        )


@router.get("/modelos/{modelo_id}", status_code=status.HTTP_200_OK)
def obter_modelo(
    modelo_id: int = Path(..., gt=0), 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Obtém informações detalhadas sobre um modelo específico.
    Requer autenticação.
    """
    try:
        # Buscar o modelo no banco de dados
        modelo = db.query(ModeloChurnEstatisticas).filter(
            ModeloChurnEstatisticas.id == modelo_id
        ).first()
        
        if not modelo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Modelo com ID {modelo_id} não encontrado"
            )
        
        # Converter para formato JSON serializável
        resultado = {
            "id": modelo.id,
            "data_criacao": modelo.data_criacao.isoformat(),
            "total_amostras": modelo.total_amostras,
            "qtd_ativos": modelo.qtd_ativos,
            "qtd_inativos": modelo.qtd_inativos,
            "acuracia": modelo.acuracia,
            "precisao": modelo.precisao,
            "recall": modelo.recall,
            "f1_score": modelo.f1_score,
            "auc": modelo.auc,
            "importancia_features": modelo.importancia_features,
            "matriz_confusao": modelo.matriz_confusao,
            "metricas_adicionais": modelo.metricas_adicionais,
            "versao_modelo": modelo.versao_modelo,
            "descricao": modelo.descricao
        }
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter detalhes do modelo: {str(e)}"
        )


@router.post("/modelo/treinar", status_code=status.HTTP_202_ACCEPTED)
def treinar_modelo(current_user: Usuario = Depends(get_current_admin_user)):
    """
    Solicita o treinamento assíncrono do modelo de previsão de churn.
    Requer autenticação de administrador.
    """
    # Enviar solicitação para a fila do RabbitMQ
    sucesso = solicitar_atualizacao_modelo()
    
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao solicitar treinamento do modelo. Verifique o serviço RabbitMQ."
        )
    
    return {"message": "Solicitação de treinamento do modelo enviada com sucesso. O processo será executado em segundo plano."}


def extrair_features_aluno(aluno_id: int, db: Session) -> Dict[str, Any]:
    """
    Extrai as características relevantes de um aluno para previsão de churn.
    """
    # Obter informações básicas do aluno
    aluno = db.query(Aluno).filter(Aluno.id == aluno_id).first()
    
    # Obter checkins do aluno
    checkins = db.query(Checkin).filter(Checkin.aluno_id == aluno_id).all()
    
    # Calcular estatísticas
    total_checkins = len(checkins)
    
    # Última visita e dias desde a última visita
    ultima_visita = db.query(Checkin.data_entrada).filter(
        Checkin.aluno_id == aluno_id
    ).order_by(Checkin.data_entrada.desc()).first()
    
    dias_desde_ultima_visita = 365  # Valor padrão alto
    if ultima_visita:
        dias_desde_ultima_visita = (datetime.now() - ultima_visita[0]).days
    
    # Duração média das visitas
    duracoes = [c.duracao_minutos for c in checkins if c.duracao_minutos is not None]
    duracao_media = sum(duracoes) / len(duracoes) if duracoes else 0
    
    # Média de visitas semanais
    if total_checkins > 0 and checkins:
        primeira_visita = min(c.data_entrada for c in checkins)
        semanas = max(1, (datetime.now() - primeira_visita).days / 7)
        media_visitas_semanais = total_checkins / semanas
    else:
        media_visitas_semanais = 0
    
    # Plano do aluno
    plano = db.query(Plano).filter(Plano.id == aluno.plano_id).first()
    
    # Criar dicionário de features
    features = {
        'total_checkins': total_checkins,
        'dias_desde_ultima_visita': dias_desde_ultima_visita,
        'duracao_media': duracao_media,
        'media_visitas_semanais': media_visitas_semanais,
        'plano_id': aluno.plano_id,
        'plano_nome': plano.nome if plano else "Desconhecido",
        'valor_mensal': plano.valor_mensal if plano else 0
    }
    
    return features 