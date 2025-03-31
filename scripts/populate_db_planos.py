from sqlalchemy.orm import Session
from app.models.database import engine
from app.models import Plano

# Criando uma sessão
session = Session(bind=engine)

# Definindo os planos
planos = [
    Plano(nome="Básico", valor=59.99),
    Plano(nome="Pro", valor=79.99),
    Plano(nome="Estudante", valor=29.99),
]

# Inserindo no banco
session.add_all(planos)
session.commit()

print("Planos adicionados com sucesso!")

# Fechando a sessão
session.close()
