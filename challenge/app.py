from fastapi import FastAPI
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent))

from api.routes import router
from models.database import Base, engine
import uvicorn

# Criar tabelas no banco se não existirem
Base.metadata.create_all(bind=engine)

# Criação da aplicação
app = FastAPI(
    # title="Academia API",
    # description="API para gerenciamento de academia de ginástica",
    # version="0.1.0",
)

# Incluir rotas
app.include_router(router)

if __name__ == "__main__":
    # uvicorn.run(app, host="0.0.0.0", port=8000)

    # Criar aluno de teste
    pass
