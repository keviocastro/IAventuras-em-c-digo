from fastapi import APIRouter

from app.api.endpoints import alunos, planos, checkins, relatorios, status, estatisticas, churn, auth

# Criar o router principal para todas as APIs
api_router = APIRouter()

# Incluir todos os routers da API
api_router.include_router(auth.router)
api_router.include_router(alunos.router)
api_router.include_router(planos.router)
api_router.include_router(checkins.router)
api_router.include_router(relatorios.router)
api_router.include_router(status.router)
api_router.include_router(estatisticas.router)
api_router.include_router(churn.router) 