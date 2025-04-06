import os
import sys
from pydantic import BaseModel

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

class CheckinPayload(BaseModel):
    id_aluno: int

class Aluno(BaseModel):
    name: str
    age: int

class Planos(BaseModel):
    name: str
    type: str
    price: float

class Matriculas(BaseModel):
    attender_id: int
    plan_id: int
    status: bool

class Checkins(BaseModel):
    id: int

class Checkouts(BaseModel):
    id: int

class ResponseStatus(BaseModel):
    status: str
    mensagem: str