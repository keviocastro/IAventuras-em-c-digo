from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# === Schemas de Alunos ===
class AlunoBase(BaseModel):
    nome: str
    email: str
    telefone: Optional[str] = None
    plano_id: int


class AlunoCreate(AlunoBase):
    pass


class AlunoResponse(AlunoBase):
    id: int
    data_cadastro: datetime

    class Config:
        from_attributes = True


# === Schemas de Planos ===
class PlanoBase(BaseModel):
    nome: str
    valor: float
    duracao_dias: int


class PlanoCreate(PlanoBase):
    pass


class PlanoResponse(PlanoBase):
    id: int

    class Config:
        from_attributes = True


# === Schemas de CheckIns ===
class CheckInBase(BaseModel):
    aluno_id: int


class CheckInCreate(CheckInBase):
    pass


class CheckInResponse(CheckInBase):
    id: int
    data_entrada: datetime
    data_saida: Optional[datetime] = None

    class Config:
        from_attributes = True
