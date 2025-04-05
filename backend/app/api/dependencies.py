from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.usuario import Usuario
from app.services.usuario_service import UsuarioService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> Usuario:
    """
    Dependência para obter o usuário atual a partir do token JWT.
    Retorna o usuário autenticado ou lança uma exceção de credenciais inválidas.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Decodificar o token
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_exception
    
    # Buscar o usuário no banco de dados
    usuario_service = UsuarioService(db)
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    
    if user is None:
        raise credentials_exception
    
    # Verificar se o usuário está ativo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo",
        )
    
    return user

def get_current_active_user(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    """
    Dependência para obter o usuário atual ativo.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo",
        )
    return current_user

def get_current_admin_user(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    """
    Dependência para verificar se o usuário atual é administrador.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores",
        )
    return current_user 