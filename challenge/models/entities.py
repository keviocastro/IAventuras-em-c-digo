from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from models.database import Base


class Plano(Base):
    __tablename__ = "planos"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    plano_nome = Column(String(100), nullable=False)

    alunos = relationship("Aluno", back_populates="plano")


class Aluno(Base):
    __tablename__ = "alunos"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    aluno_status = Column(String(20), default="ativo")
    plano_id = Column(Integer, ForeignKey("planos.id"))

    plano = relationship("Plano", back_populates="alunos")
    checkins = relationship("CheckIn", back_populates="aluno")


class CheckIn(Base):
    __tablename__ = "checkins"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"), nullable=False)
    data_entrada = Column(DateTime, default=datetime.now)
    duracao_treino = Column(Integer)  # em minutos

    aluno = relationship("Aluno", back_populates="checkins")
