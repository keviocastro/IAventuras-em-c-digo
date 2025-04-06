from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# === Schemas de Alunos ===
class AlunoBase(BaseModel):
    nome: str
    email: EmailStr
    telefone: Optional[str] = None
    data_nascimento: Optional[datetime] = None
    sexo: Optional[str] = None
    endereco: Optional[str] = None
    plano_id: Optional[int] = None
    status: Optional[str] = None


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
    descricao: Optional[str] = None
    valor_mensal: float
    periodo_contrato: Optional[int] = 1
    ativo: Optional[bool] = True
    data_criacao: Optional[datetime] = datetime.now().isoformat()


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
    data_saida: Optional[datetime] = None
    duracao: Optional[int] = None  # em minutos
    observacao: Optional[str] = None


class CheckInCreate(CheckInBase):
    data_entrada: Optional[datetime] = None
    data_saida: Optional[datetime] = None
    duracao: Optional[int] = None
    observacao: Optional[str] = None


class CheckOutUpdate(BaseModel):
    aluno_id: int
    data_saida: datetime
    duracao: Optional[int] = None
    observacao: Optional[str] = None


class CheckInResponse(CheckInBase):
    aluno_id: int
    data_entrada: Optional[datetime] = None
    data_saida: Optional[datetime] = None
    duracao: Optional[int] = None  # em minutos
    observacao: Optional[str] = None

    class Config:
        from_attributes = True


class CheckInBatchCreate(BaseModel):
    aluno_id: int
    timestamp: Optional[str] = None
    entrada: bool = True
