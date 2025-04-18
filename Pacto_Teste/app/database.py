from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

# Use a variável de ambiente DATABASE_URL definida no docker-compose.yml
URL_DATABASE = os.getenv("DATABASE_URL", "postgresql://postgres:005@localhost/Academia_db2")

if not URL_DATABASE:
    raise ValueError("A variável de ambiente DATABASE_URL não foi definida.")

engine = create_engine(URL_DATABASE)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()