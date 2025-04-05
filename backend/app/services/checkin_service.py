from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, date, timedelta

from app.models.aluno import Checkin, Aluno
from app.schemas.aluno import CheckinCreate


class CheckinService:  
    def __init__(self, db: Session):
        self.db = db

    def obter_checkin_por_id(self, checkin_id: int) -> Optional[Checkin]:
        """
        Obtém um checkin pelo seu ID.
        """
        return self.db.query(Checkin).filter(Checkin.id == checkin_id).first()

    def listar_checkins(
        self, 
        skip: int = 0, 
        limit: int = 100,
        aluno_id: Optional[int] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None
    ) -> List[Checkin]:
        """
        Lista todos os checkins com filtros opcionais.
        """
        query = self.db.query(Checkin)
        
        # Aplicar filtros
        if aluno_id:
            query = query.filter(Checkin.aluno_id == aluno_id)
        
        if data_inicio:
            data_inicio_dt = datetime.combine(data_inicio, datetime.min.time())
            query = query.filter(Checkin.data_entrada >= data_inicio_dt)
        
        if data_fim:
            data_fim_dt = datetime.combine(data_fim, datetime.max.time())
            query = query.filter(Checkin.data_entrada <= data_fim_dt)
        
        # Ordenar por data de entrada (mais recentes primeiro)
        query = query.order_by(Checkin.data_entrada.desc())
        
        return query.offset(skip).limit(limit).all()

    def listar_checkins_ativos(self) -> List[Checkin]:
        """
        Lista todos os checkins ativos (sem data de saída).
        """
        return self.db.query(Checkin).filter(Checkin.data_saida.is_(None)).all()

    def listar_checkins_por_aluno(self, aluno_id: int) -> List[Checkin]:
        """
        Lista todos os checkins de um aluno específico.
        """
        return self.db.query(Checkin).filter(Checkin.aluno_id == aluno_id).order_by(Checkin.data_entrada.desc()).all()

    def registrar_checkin(self, checkin: CheckinCreate) -> Checkin:
        """
        Registra uma entrada do aluno na academia.
        """
        # Verificar se o aluno existe
        aluno = self.db.query(Aluno).filter(Aluno.id == checkin.aluno_id).first()
        if not aluno:
            raise ValueError(f"Aluno com ID {checkin.aluno_id} não encontrado")

        # Verificar se o aluno já está na academia (sem data de saída)
        checkin_aberto = self.db.query(Checkin).filter(
            Checkin.aluno_id == checkin.aluno_id,
            Checkin.data_saida.is_(None)
        ).first()

        if checkin_aberto:
            # Se já houver um checkin aberto, registra a saída
            agora = datetime.now()
            duracao = (agora - checkin_aberto.data_entrada).total_seconds() / 60
            checkin_aberto.data_saida = agora
            checkin_aberto.duracao_minutos = int(duracao)
            self.db.commit()
            self.db.refresh(checkin_aberto)
            return checkin_aberto
        else:
            # Registrar novo checkin
            db_checkin = Checkin(
                aluno_id=checkin.aluno_id,
                data_entrada=datetime.now()
            )
            self.db.add(db_checkin)
            self.db.commit()
            self.db.refresh(db_checkin)
            return db_checkin

    def remover_checkin(self, checkin_id: int) -> None:
        """
        Remove um checkin do banco de dados.
        """
        # Obter o checkin existente
        db_checkin = self.obter_checkin_por_id(checkin_id)
        if not db_checkin:
            raise ValueError(f"Checkin com ID {checkin_id} não encontrado")

        # Remover o checkin
        self.db.delete(db_checkin)
        self.db.commit()

        return None

    def obter_estatisticas_frequencia(self, aluno_id: int, periodo_dias: int = 30) -> dict:
        """
        Obtém estatísticas de frequência de um aluno em um período específico.
        """
        # Verificar se o aluno existe
        aluno = self.db.query(Aluno).filter(Aluno.id == aluno_id).first()
        if not aluno:
            raise ValueError(f"Aluno com ID {aluno_id} não encontrado")
        
        # Definir o período de análise
        data_limite = datetime.now() - timedelta(days=periodo_dias)
        
        # Obter checkins no período
        checkins_periodo = self.db.query(Checkin).filter(
            Checkin.aluno_id == aluno_id,
            Checkin.data_entrada >= data_limite
        ).all()
        
        # Calcular estatísticas
        total_visitas = len(checkins_periodo)
        
        # Duração média das visitas
        checkins_com_duracao = [c for c in checkins_periodo if c.duracao_minutos is not None]
        duracao_media = 0
        if checkins_com_duracao:
            duracao_media = sum(c.duracao_minutos for c in checkins_com_duracao) / len(checkins_com_duracao)
        
        # Dias por semana (média)
        dias_distintos = set()
        for checkin in checkins_periodo:
            dias_distintos.add(checkin.data_entrada.date())
        
        visitas_por_semana = (len(dias_distintos) / periodo_dias) * 7
        
        return {
            "total_visitas": total_visitas,
            "duracao_media_minutos": round(duracao_media, 2),
            "visitas_por_semana": round(visitas_por_semana, 2),
            "dias_distintos": len(dias_distintos),
            "periodo_dias": periodo_dias
        } 