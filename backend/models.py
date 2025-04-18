from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Numeric, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class Plano(Base):
    __tablename__ = 'planos'
    id = Column(Integer, primary_key=True)
    duracao = Column(Integer, nullable=False)
    preco = Column(Numeric, nullable=False)
    descricao = Column(Text, nullable=False)

class Aluno(Base):
    __tablename__ = 'alunos'
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    cpf = Column(String(16), nullable=False, unique=True)
    plano_id = Column(Integer, ForeignKey('planos.id'), nullable=False)
    plano = relationship("Plano", back_populates="alunos")

class Checkin(Base):
    __tablename__ = 'checkins'
    id = Column(Integer, primary_key=True)
    aluno_id = Column(Integer, ForeignKey('alunos.id'), nullable=False)
    checkin = Column(DateTime)
    checkout = Column(DateTime)
    aluno = relationship("Aluno", back_populates="checkins")

Plano.alunos = relationship("Aluno", back_populates="plano", cascade="all, delete-orphan")
Aluno.checkins = relationship("Checkin", back_populates="aluno", cascade="all, delete-orphan")
