from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Date, Time
from app.database import Base

class Aluno(Base):
    __tablename__ = "alunos"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String, index=True)
    plano = Column(String, index=True)
    risco_churn = Column(Integer, index=True)

class checkins(Base):
    __tablename__ = "checkins"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    aluno_id = Column(Integer, ForeignKey("alunos.id"))
    data = Column(Date)
    horario_checkin = Column(Time, index=True)
    horario_checkout = Column(Time, index=True)

class planos(Base):
    __tablename__ = "planos"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String, index=True)
    valor = Column(String, index=True)
    duracao = Column(String, index=True)