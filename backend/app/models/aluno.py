from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Date, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.db.database import Base


class Plano(Base):
    __tablename__ = "planos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    descricao = Column(String)
    valor_mensal = Column(Float, nullable=False)
    
    # Relacionamento com alunos
    alunos = relationship("Aluno", back_populates="plano")


class Aluno(Base):
    __tablename__ = "alunos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    telefone = Column(String(20))
    data_nascimento = Column(Date, nullable=True)
    data_inscricao = Column(DateTime, default=datetime.now)
    ativo = Column(Integer, default=1)  # 1 = ativo, 0 = inativo
    plano_id = Column(Integer, ForeignKey("planos.id"), nullable=True)
    
    # Relacionamentos
    plano = relationship("Plano", back_populates="alunos")
    checkins = relationship("Checkin", back_populates="aluno", cascade="all, delete-orphan")
    probabilidade_churn = relationship("ChurnProbability", back_populates="aluno", uselist=False, cascade="all, delete-orphan")


class Checkin(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"))
    data_entrada = Column(DateTime, default=func.now())
    data_saida = Column(DateTime, nullable=True)
    duracao_minutos = Column(Integer, nullable=True)
    
    # Relacionamento
    aluno = relationship("Aluno", back_populates="checkins") 


class ChurnProbability(Base):
    """
    Modelo para armazenar a probabilidade de churn calculada para cada aluno.
    """
    __tablename__ = "churn_probabilidades"
    
    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"), unique=True, nullable=False)
    probabilidade = Column(Float, nullable=False)
    fatores_risco = Column(String(500), nullable=True)
    data_calculo = Column(DateTime, default=datetime.now)
    ultima_atualizacao = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relacionamentos
    aluno = relationship("Aluno", back_populates="probabilidade_churn")


class ModeloChurnEstatisticas(Base):
    """
    Modelo para armazenar estatísticas dos modelos de churn treinados.
    """
    __tablename__ = "modelo_churn_estatisticas"
    
    id = Column(Integer, primary_key=True, index=True)
    data_criacao = Column(DateTime, default=datetime.now)
    total_amostras = Column(Integer, nullable=False)
    qtd_ativos = Column(Integer, nullable=False)
    qtd_inativos = Column(Integer, nullable=False)
    acuracia = Column(Float, nullable=True)
    precisao = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    auc = Column(Float, nullable=True)
    importancia_features = Column(JSON, nullable=True)
    matriz_confusao = Column(JSON, nullable=True)
    metricas_adicionais = Column(JSON, nullable=True)
    versao_modelo = Column(String(50), nullable=True)
    descricao = Column(String(500), nullable=True) 