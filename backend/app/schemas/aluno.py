from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator


# Schemas para Plano
class PlanoBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    valor_mensal: float


class PlanoCreate(PlanoBase):
    pass


class PlanoResponse(PlanoBase):
    id: int

    class Config:
        from_attributes = True


# Schemas para Aluno
class AlunoBase(BaseModel):
    nome: str
    email: EmailStr
    telefone: Optional[str] = None
    data_nascimento: Optional[datetime] = None
    plano_id: int


class AlunoCreate(AlunoBase):
    pass


class AlunoResponse(AlunoBase):
    id: int
    data_inscricao: datetime
    ativo: int = 1
    plano: Optional[PlanoResponse] = None

    class Config:
        from_attributes = True


# Schemas para Checkin
class CheckinBase(BaseModel):
    aluno_id: int


class CheckinCreate(CheckinBase):
    pass


class CheckinResponse(CheckinBase):
    id: int
    data_entrada: datetime
    data_saida: Optional[datetime] = None
    duracao_minutos: Optional[int] = None

    class Config:
        from_attributes = True


# Schemas para Frequência
class FrequenciaItem(BaseModel):
    data_entrada: datetime
    data_saida: Optional[datetime] = None
    duracao_minutos: Optional[int] = None


class FrequenciaResponse(BaseModel):
    aluno_id: int
    checkins: List[FrequenciaItem]
    total_visitas: int
    media_visitas_semanais: float
    media_duracao_minutos: Optional[float] = None

    class Config:
        from_attributes = True


# Schema para Risco de Churn
class RiscoChurnResponse(BaseModel):
    aluno_id: int
    probabilidade_churn: float = Field(..., ge=0, le=1)
    fatores_risco: List[str]
    ultima_visita: Optional[datetime] = None
    dias_desde_ultima_visita: Optional[int] = None
    recomendacoes: List[str]

    class Config:
        from_attributes = True


# Schema para armazenar probabilidade de churn no banco de dados
class ChurnProbabilityCreate(BaseModel):
    aluno_id: int
    probabilidade: float = Field(..., ge=0, le=1)
    fatores_risco: str

    class Config:
        from_attributes = True


# Schema para resposta de probabilidade de churn do banco de dados
class ChurnProbabilityResponse(BaseModel):
    id: int
    aluno_id: int
    probabilidade: float
    fatores_risco: str
    data_calculo: datetime
    ultima_atualizacao: datetime

    class Config:
        from_attributes = True


# Schema para lista de alunos com probabilidade de churn
class AlunoChurnResponse(BaseModel):
    aluno_id: int
    nome: str
    email: str
    ativo: int
    plano_nome: Optional[str] = None
    probabilidade_churn: float = Field(0.0, ge=0, le=1)
    ultima_visita: Optional[datetime] = None
    dias_desde_ultima_visita: Optional[int] = None
    
    class Config:
        from_attributes = True


# Schema para os top alunos com maior risco de churn
class TopChurnRiskResponse(BaseModel):
    alunos_risco: List[AlunoChurnResponse]
    
    class Config:
        from_attributes = True 