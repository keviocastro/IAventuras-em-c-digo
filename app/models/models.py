from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.database import Base

# Modelo da tabela de planos
class Plano(Base):
    __tablename__ = "planos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(50), nullable=False)
    valor = Column(Float, nullable=False)

    # Relacionamento inverso (Plano pode ter muitos alunos)
    alunos = relationship("Aluno", back_populates="plano")

    def __repr__(self):
        return f"<Plano {self.nome} - {self.valor}>"

# Modelo da tabela de alunos
class Aluno(Base):
    __tablename__ = "alunos"

    # Número de matrícula (chave primária)
    matricula = Column(Integer, primary_key=True, autoincrement=True)

    # Informações do aluno
    nome = Column(String(100), nullable=False)
    data_nascimento = Column(Date, nullable=True)
    genero = Column(String(15), nullable=True)
    email = Column(String(100), unique=True, nullable=False)

    # Informações da matrícula
    plano_id = Column(Integer, ForeignKey("planos.id"), nullable=False)
    data_matricula = Column(Date, default=datetime.utcnow, nullable=False)
    matricula_ativa = Column(Boolean, default=True, nullable=False)
    data_cancelamento = Column(Date, nullable=True)

    # Relacionamento com a tabela Plano
    plano = relationship("Plano", back_populates="alunos")

    def __repr__(self):
        return f"<Aluno {self.nome}>"

# Modelo da tabela de check-ins
class Checkin(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True)
    aluno_id = Column(Integer, ForeignKey("alunos.matricula"), nullable=False)
    data_hora_entrada = Column(DateTime, nullable=False, default=datetime.utcnow)
    data_hora_saida = Column(DateTime, nullable=True)  # Pode ser NULL se o aluno ainda não saiu

    aluno = relationship("Aluno", back_populates="checkins")

    def __repr__(self):
        return f"<Checkin {self.id} - Aluno {self.aluno_id}>"
