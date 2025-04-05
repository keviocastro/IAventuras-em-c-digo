from app.db.database import engine
from app.models.aluno import Base

def init_db():
    """
    Inicializa o banco de dados criando todas as tabelas definidas nos modelos.
    """
    print("Criando tabelas no banco de dados...")
    Base.metadata.create_all(bind=engine)
    print("Tabelas criadas com sucesso!")

if __name__ == "__main__":
    init_db() 