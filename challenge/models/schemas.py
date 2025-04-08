from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# === Schemas de Alunos ===
class AlunoBase(BaseModel):
    aluno_status: Optional[str] = "ativo"
    plano_id: Optional[int] = None


class AlunoCreate(AlunoBase):
    pass


class AlunoResponse(AlunoBase):
    id: int

    class Config:
        from_attributes = True


# === Schemas de Planos ===
class PlanoBase(BaseModel):
    plano_nome: str


class PlanoCreate(PlanoBase):
    pass


class PlanoResponse(PlanoBase):
    id: int

    class Config:
        from_attributes = True


# === Schemas de CheckIns ===
class CheckInBase(BaseModel):
    aluno_id: int
    data_entrada: Optional[datetime] = None
    duracao_treino: Optional[int] = None  # em minutos


class CheckInCreate(CheckInBase):
    pass


class CheckInResponse(CheckInBase):
    id: int

    class Config:
        from_attributes = True


class CheckInUpdate(CheckInBase):
    pass


class CheckInBatchCreate(BaseModel):
    aluno_id: int
    timestamp: Optional[str] = None
    entrada: bool = True
