from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from challenge.models.database import Base


class Aluno(Base):
    __tablename__ = "alunos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    telefone = Column(String)
    data_nascimento = Column(DateTime)
    sexo = Column(String)
    endereco = Column(String)
    data_cadastro = Column(DateTime, default=datetime.now)
    plano_id = Column(Integer, ForeignKey("planos.id"))
    status = Column(String, default="ativo")

    # Relacionamentos
    plano = relationship("Plano", back_populates="alunos")
    checkins = relationship("CheckIn", back_populates="aluno")


class Plano(Base):
    __tablename__ = "planos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    descricao = Column(String)
    valor_mensal = Column(Float)
    periodo_contrato = Column(Integer, default=1)
    ativo = Column(String, default="ativo")
    data_criacao = Column(DateTime, default=datetime.now)

    # Relacionamentos
    alunos = relationship("Aluno", back_populates="plano")


class CheckIn(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"))
    data_entrada = Column(DateTime, default=datetime.now)
    data_saida = Column(DateTime, nullable=True)
    duracao = Column(Integer)  # em minutos
    observacao = Column(String)

    # Relacionamentos
    aluno = relationship("Aluno", back_populates="checkins")
