from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.usuario import Usuario
from app.schemas.auth import UserCreate, UserResponse
from app.core.security import get_password_hash, verify_password

class UsuarioService:
    """
    Serviço para gerenciamento de usuários.
    """
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_username(self, username: str) -> Usuario:
        """Busca um usuário pelo nome de usuário"""
        return self.db.query(Usuario).filter(Usuario.username == username).first()
    
    def get_user_by_email(self, email: str) -> Usuario:
        """Busca um usuário pelo email"""
        return self.db.query(Usuario).filter(Usuario.email == email).first()
    
    def authenticate_user(self, username: str, password: str) -> Usuario:
        """Autentica um usuário pelo nome de usuário e senha"""
        user = self.get_user_by_username(username)
        
        if not user:
            return False
        
        if not verify_password(password, user.hashed_password):
            return False
        
        return user
    
    def create_user(self, user_data: UserCreate) -> Usuario:
        """Cria um novo usuário"""
        # Verificar se o nome de usuário já existe
        db_user = self.get_user_by_username(user_data.username)
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nome de usuário já utilizado"
            )
        
        # Verificar se o email já existe
        db_user = self.get_user_by_email(user_data.email)
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já cadastrado"
            )
        
        # Criar o usuário
        hashed_password = get_password_hash(user_data.password)
        db_user = Usuario(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            is_admin=user_data.is_admin
        )
        
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        return db_user
    
    def get_users(self, skip: int = 0, limit: int = 100):
        """Lista todos os usuários"""
        return self.db.query(Usuario).offset(skip).limit(limit).all()
    
    def create_admin_user(self, username: str, email: str, password: str) -> Usuario:
        """
        Cria um usuário administrador 
        (função especial para criação inicial de admin)
        """
        # Verificar se já existe um usuário com este nome
        existing_user = self.get_user_by_username(username)
        if existing_user:
            return existing_user
            
        # Criar dados do usuário admin
        user_data = UserCreate(
            username=username,
            email=email,
            password=password,
            is_admin=True
        )
        
        # Criar usuário admin
        return self.create_user(user_data) 