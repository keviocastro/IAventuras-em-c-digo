from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.auth import Token, UserCreate, UserResponse
from app.services.usuario_service import UsuarioService
from app.core.security import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_active_user, get_current_admin_user
from app.models.usuario import Usuario

router = APIRouter(prefix="/auth", tags=["autenticação"])

@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Endpoint OAuth2 para obter um token de acesso JWT.
    """
    user = UsuarioService(db).authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome de usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Criar token JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id
        }, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    user: UserCreate, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_admin_user)
):
    """
    Registra um novo usuário no sistema.
    
    Apenas administradores podem registrar novos usuários.
    """
    return UsuarioService(db).create_user(user)

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: Usuario = Depends(get_current_active_user)):
    """
    Retorna informações do usuário autenticado atualmente.
    """
    return current_user 