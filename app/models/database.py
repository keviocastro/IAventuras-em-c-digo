from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# URL do banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://pacto:pacto123@localhost/academia")

# Criar a engine de conexão
engine = create_engine(DATABASE_URL)

# Criar uma sessão para interagir com o banco
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para os modelos do SQLAlchemy
Base = declarative_base()

# Função para obter a sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()