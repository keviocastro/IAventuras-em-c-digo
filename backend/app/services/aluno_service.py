import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

from app.models.aluno import Aluno, Checkin, Plano
from app.schemas.aluno import AlunoCreate, CheckinCreate, FrequenciaResponse, RiscoChurnResponse, FrequenciaItem
from app.core.cache import get_cache

# Tempo de expiração do cache (em segundos)
CACHE_EXPIRE_CHURN = 24 * 60 * 60  # 24 horas
CACHE_EXPIRE_FREQUENCIA = 12 * 60 * 60  # 12 horas


class AlunoService:
    def __init__(self, db: Session):
        self.db = db
        self.cache = get_cache()

    def obter_aluno_por_id(self, aluno_id: int) -> Optional[Aluno]:
        """
        Obtém um aluno pelo seu ID.
        """
        return self.db.query(Aluno).filter(Aluno.id == aluno_id).first()

    def obter_aluno_por_email(self, email: str) -> Optional[Aluno]:
        """
        Obtém um aluno pelo seu email.
        """
        return self.db.query(Aluno).filter(Aluno.email == email).first()

    def listar_alunos(self, skip: int = 0, limit: int = 100, nome: Optional[str] = None, 
                      email: Optional[str] = None, ativo: Optional[int] = None) -> List[Aluno]:
        """
        Lista todos os alunos com filtros opcionais.
        """
        query = self.db.query(Aluno)
        
        # Aplicar filtros se fornecidos
        if nome:
            query = query.filter(Aluno.nome.ilike(f"%{nome}%"))
        if email:
            query = query.filter(Aluno.email.ilike(f"%{email}%"))
        if ativo is not None:
            query = query.filter(Aluno.ativo == ativo)
            
        # Aplicar paginação
        return query.offset(skip).limit(limit).all()

    def criar_aluno(self, aluno: AlunoCreate) -> Aluno:
        """
        Cria um novo aluno no banco de dados.
        """
        # Verificar se o plano existe
        plano = self.db.query(Plano).filter(Plano.id == aluno.plano_id).first()
        if not plano:
            raise ValueError(f"Plano com ID {aluno.plano_id} não encontrado")

        # Verificar se já existe um aluno com o mesmo email
        db_aluno = self.obter_aluno_por_email(aluno.email)
        if db_aluno:
            raise ValueError(f"Já existe um aluno cadastrado com o email {aluno.email}")

        # Criar o objeto Aluno
        db_aluno = Aluno(
            nome=aluno.nome,
            email=aluno.email,
            telefone=aluno.telefone,
            data_nascimento=aluno.data_nascimento,
            plano_id=aluno.plano_id
        )

        # Salvar no banco de dados
        self.db.add(db_aluno)
        self.db.commit()
        self.db.refresh(db_aluno)

        return db_aluno

    def registrar_checkin(self, checkin: CheckinCreate) -> Checkin:
        """
        Registra uma entrada do aluno na academia.
        """
        # Verificar se o aluno existe
        aluno = self.obter_aluno_por_id(checkin.aluno_id)
        if not aluno:
            raise ValueError(f"Aluno com ID {checkin.aluno_id} não encontrado")

        # Verificar se o aluno já está na academia (sem data de saída)
        checkin_aberto = self.db.query(Checkin).filter(
            Checkin.aluno_id == checkin.aluno_id,
            Checkin.data_saida.is_(None)
        ).first()

        if checkin_aberto:
            # Se já houver um checkin aberto, registra a saída
            agora = datetime.datetime.now()
            duracao = (agora - checkin_aberto.data_entrada).total_seconds() / 60
            checkin_aberto.data_saida = agora
            checkin_aberto.duracao_minutos = int(duracao)
            self.db.commit()
            self.db.refresh(checkin_aberto)
            
            # Invalidar cache de frequência e churn
            self._invalidar_cache_aluno(checkin.aluno_id)
            
            return checkin_aberto
        else:
            # Registrar novo checkin
            db_checkin = Checkin(
                aluno_id=checkin.aluno_id,
                data_entrada=datetime.datetime.now()
            )
            self.db.add(db_checkin)
            self.db.commit()
            self.db.refresh(db_checkin)
            
            # Invalidar cache de frequência e churn
            self._invalidar_cache_aluno(checkin.aluno_id)
            
            return db_checkin

    def _invalidar_cache_aluno(self, aluno_id: int):
        """
        Invalida o cache relacionado a um aluno específico.
        """
        if not self.cache.is_available():
            return
            
        # Remover cache de frequência
        self.cache.delete(f"frequencia:aluno:{aluno_id}")
        
        # Remover cache de churn
        self.cache.delete(f"churn:aluno:{aluno_id}")

    def obter_frequencia(self, aluno_id: int) -> FrequenciaResponse:
        """
        Obtém o histórico de frequência do aluno.
        """
        # Verificar no cache primeiro
        if self.cache.is_available():
            cache_key = f"frequencia:aluno:{aluno_id}"
            frequencia_cache = self.cache.get(cache_key)
            if frequencia_cache:
                # Converter de volta para FrequenciaResponse
                return FrequenciaResponse(**frequencia_cache)
        
        # Se não estiver em cache, buscar do banco de dados
        # Verificar se o aluno existe
        aluno = self.obter_aluno_por_id(aluno_id)
        if not aluno:
            raise ValueError(f"Aluno com ID {aluno_id} não encontrado")

        # Obter todos os checkins do aluno
        checkins_db = self.db.query(Checkin).filter(Checkin.aluno_id == aluno_id).all()
        
        # Converter objetos Checkin em FrequenciaItem
        checkins = [
            FrequenciaItem(
                data_entrada=c.data_entrada,
                data_saida=c.data_saida,
                duracao_minutos=c.duracao_minutos
            ) for c in checkins_db
        ]
        
        # Calcular estatísticas
        total_visitas = len(checkins)
        
        # Data da primeira visita
        primeira_visita = None
        if total_visitas > 0:
            primeira_visita = min(c.data_entrada for c in checkins)
        
        # Calcular média de visitas semanais
        if primeira_visita:
            hoje = datetime.datetime.now()
            semanas = (hoje - primeira_visita).days / 7
            media_visitas_semanais = total_visitas / max(1, semanas)
        else:
            media_visitas_semanais = 0
        
        # Calcular média de duração em minutos
        checkins_com_duracao = [c for c in checkins if c.duracao_minutos is not None]
        if checkins_com_duracao:
            media_duracao = sum(c.duracao_minutos for c in checkins_com_duracao) / len(checkins_com_duracao)
        else:
            media_duracao = None
        
        frequencia = FrequenciaResponse(
            aluno_id=aluno_id,
            checkins=checkins,
            total_visitas=total_visitas,
            media_visitas_semanais=round(media_visitas_semanais, 2),
            media_duracao_minutos=round(media_duracao, 2) if media_duracao else None
        )
        
        # Armazenar no cache com expiração de 12 horas
        if self.cache.is_available():
            self.cache.set(f"frequencia:aluno:{aluno_id}", frequencia.dict(), CACHE_EXPIRE_FREQUENCIA)
        
        return frequencia

    def calcular_risco_churn(self, aluno_id: int) -> RiscoChurnResponse:
        """
        Calcula a probabilidade de desistência (churn) do aluno.
        """
        # Verificar no cache primeiro
        if self.cache.is_available():
            cache_key = f"churn:aluno:{aluno_id}"
            churn_cache = self.cache.get(cache_key)
            if churn_cache:
                # Converter de volta para RiscoChurnResponse
                return RiscoChurnResponse(**churn_cache)
        
        # Se não estiver em cache, calcular
        # Verificar se o aluno existe
        aluno = self.obter_aluno_por_id(aluno_id)
        if not aluno:
            raise ValueError(f"Aluno com ID {aluno_id} não encontrado")
        
        # Obter última visita
        ultima_visita = self.db.query(
            func.max(Checkin.data_entrada)
        ).filter(Checkin.aluno_id == aluno_id).scalar()
        
        # Calcular dias desde a última visita
        hoje = datetime.datetime.now()
        dias_desde_ultima_visita = None
        if ultima_visita:
            dias_desde_ultima_visita = (hoje - ultima_visita).days
        
        # Obter frequência
        frequencia = self.obter_frequencia(aluno_id)
        
        # Modelo simplificado para cálculo de churn
        # Fatores de risco:
        # 1. Dias desde a última visita
        # 2. Média de visitas semanais
        # 3. Duração média das visitas
        
        fatores_risco = []
        recomendacoes = []
        probabilidade = 0.0
        
        # 1. Analise de dias sem visitar
        if dias_desde_ultima_visita:
            if dias_desde_ultima_visita > 30:
                probabilidade += 0.4
                fatores_risco.append(f"Inatividade há {dias_desde_ultima_visita} dias")
                recomendacoes.append("Enviar e-mail incentivando retorno")
            elif dias_desde_ultima_visita > 14:
                probabilidade += 0.2
                fatores_risco.append(f"Inatividade há {dias_desde_ultima_visita} dias")
                recomendacoes.append("Enviar mensagem lembrando da academia")
        
        # 2. Análise de frequência semanal
        if frequencia.media_visitas_semanais < 1:
            probabilidade += 0.3
            fatores_risco.append(f"Baixa frequência (média de {frequencia.media_visitas_semanais:.1f} visitas por semana)")
            recomendacoes.append("Oferecer programa de incentivo à frequência")
        elif frequencia.media_visitas_semanais < 2:
            probabilidade += 0.15
            fatores_risco.append(f"Frequência moderada (média de {frequencia.media_visitas_semanais:.1f} visitas por semana)")
            recomendacoes.append("Sugerir aulas em grupo para aumentar motivação")
        
        # 3. Análise da duração das visitas
        if frequencia.media_duracao_minutos and frequencia.media_duracao_minutos < 30:
            probabilidade += 0.1
            fatores_risco.append(f"Visitas curtas (média de {frequencia.media_duracao_minutos:.0f} minutos por visita)")
            recomendacoes.append("Oferecer avaliação física gratuita para revisar treino")
        
        # Limite a probabilidade a 0.95 (95%)
        probabilidade = min(0.95, probabilidade)
        
        # Se não houver fatores de risco identificados
        if not fatores_risco:
            fatores_risco.append("Nenhum fator de risco significativo")
            recomendacoes.append("Manter acompanhamento padrão")
        
        resultado = RiscoChurnResponse(
            aluno_id=aluno_id,
            probabilidade_churn=probabilidade,
            fatores_risco=fatores_risco,
            ultima_visita=ultima_visita,
            dias_desde_ultima_visita=dias_desde_ultima_visita,
            recomendacoes=recomendacoes
        )
        
        # Armazenar no cache com expiração de 24 horas
        if self.cache.is_available():
            self.cache.set(f"churn:aluno:{aluno_id}", resultado.dict(), CACHE_EXPIRE_CHURN)
        
        return resultado

    def atualizar_aluno(self, aluno_id: int, aluno: AlunoCreate) -> Aluno:
        """
        Atualiza as informações de um aluno existente.
        """
        # Obter aluno existente
        db_aluno = self.obter_aluno_por_id(aluno_id)
        if not db_aluno:
            raise ValueError(f"Aluno com ID {aluno_id} não encontrado")
        
        # Verificar se o email já está em uso por outro aluno
        if aluno.email != db_aluno.email:
            aluno_email = self.obter_aluno_por_email(aluno.email)
            if aluno_email and aluno_email.id != aluno_id:
                raise ValueError(f"Email {aluno.email} já está em uso por outro aluno")
        
        # Verificar se o plano existe
        plano = self.db.query(Plano).filter(Plano.id == aluno.plano_id).first()
        if not plano:
            raise ValueError(f"Plano com ID {aluno.plano_id} não encontrado")
        
        # Atualizar atributos
        db_aluno.nome = aluno.nome
        db_aluno.email = aluno.email
        db_aluno.telefone = aluno.telefone
        db_aluno.data_nascimento = aluno.data_nascimento
        db_aluno.plano_id = aluno.plano_id
        
        # Salvar alterações
        self.db.commit()
        self.db.refresh(db_aluno)
        
        # Invalidar cache
        self._invalidar_cache_aluno(aluno_id)
        
        return db_aluno
    
    def atualizar_status_aluno(self, aluno_id: int, ativo: int) -> Aluno:
        """
        Atualiza o status de um aluno (ativo/inativo).
        """
        # Obter aluno existente
        db_aluno = self.obter_aluno_por_id(aluno_id)
        if not db_aluno:
            raise ValueError(f"Aluno com ID {aluno_id} não encontrado")
        
        # Atualizar status
        db_aluno.ativo = ativo
        
        # Salvar alterações
        self.db.commit()
        self.db.refresh(db_aluno)
        
        # Invalidar cache
        self._invalidar_cache_aluno(aluno_id)
        
        return db_aluno 