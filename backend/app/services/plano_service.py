from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.aluno import Plano
from app.schemas.aluno import PlanoCreate, PlanoResponse


class PlanoService:
    def __init__(self, db: Session):
        self.db = db

    def obter_plano_por_id(self, plano_id: int) -> Optional[Plano]:
        """
        Obtém um plano pelo seu ID.
        """
        return self.db.query(Plano).filter(Plano.id == plano_id).first()

    def listar_planos(self, skip: int = 0, limit: int = 100) -> List[Plano]:
        """
        Lista todos os planos disponíveis.
        """
        return self.db.query(Plano).offset(skip).limit(limit).all()

    def criar_plano(self, plano: PlanoCreate) -> Plano:
        """
        Cria um novo plano no banco de dados.
        """
        # Criar o objeto Plano
        db_plano = Plano(
            nome=plano.nome,
            descricao=plano.descricao,
            valor_mensal=plano.valor_mensal
        )

        # Salvar no banco de dados
        self.db.add(db_plano)
        self.db.commit()
        self.db.refresh(db_plano)

        return db_plano

    def atualizar_plano(self, plano_id: int, plano: PlanoCreate) -> Plano:
        """
        Atualiza um plano existente.
        """
        # Obter o plano existente
        db_plano = self.obter_plano_por_id(plano_id)
        if not db_plano:
            raise ValueError(f"Plano com ID {plano_id} não encontrado")

        # Atualizar os campos
        db_plano.nome = plano.nome
        db_plano.descricao = plano.descricao
        db_plano.valor_mensal = plano.valor_mensal

        # Salvar as alterações
        self.db.commit()
        self.db.refresh(db_plano)

        return db_plano

    def remover_plano(self, plano_id: int) -> None:
        """
        Remove um plano do banco de dados.
        """
        # Obter o plano existente
        db_plano = self.obter_plano_por_id(plano_id)
        if not db_plano:
            raise ValueError(f"Plano com ID {plano_id} não encontrado")

        # Verificar se o plano está sendo usado por algum aluno
        if db_plano.alunos and len(db_plano.alunos) > 0:
            raise ValueError(f"Não é possível remover este plano pois existem {len(db_plano.alunos)} alunos associados a ele")

        # Remover o plano
        self.db.delete(db_plano)
        self.db.commit()

        return None 