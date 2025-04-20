from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Obtém a senha do ambiente ou usa um valor padrão para desenvolvimento local
PASSWORD = os.getenv("DB_PASSWORD", "")

# Configuração de conexão
SQLALCHEMY_DATABASE_URL = (
    f"postgresql://postgres:{PASSWORD}@localhost:5432/postgres"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Função para obter conexão com banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
