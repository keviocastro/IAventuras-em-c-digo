from fastapi import FastAPI
from challenge.api.routes import router
from challenge.models.database import Base, engine

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
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
