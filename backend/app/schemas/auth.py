from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """Esquema base para usuários"""
    username: str
    email: EmailStr

class UserCreate(UserBase):
    """Esquema para criação de usuários"""
    password: str
    is_admin: Optional[bool] = False

class UserResponse(UserBase):
    """Esquema para resposta de usuários"""
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    """Esquema para login de usuários"""
    username: str
    password: str

class Token(BaseModel):
    """Esquema para token de acesso"""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Esquema para dados do token"""
    username: Optional[str] = None 