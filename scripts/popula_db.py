import sys
import os
import datetime
import random
from pathlib import Path

# Adiciona a pasta backend ao PYTHONPATH
backend_dir = str(Path(__file__).parent.parent / "backend")
sys.path.insert(0, backend_dir)

from sqlalchemy.orm import Session

from app.db.database import Base, engine, SessionLocal
from app.models.aluno import Aluno, Plano, Checkin


def criar_planos(db: Session):
    """
    Cria planos básicos se eles não existirem.
    """
    planos = [
        {"nome": "Básico", "descricao": "Acesso à musculação em horário comercial", "valor_mensal": 99.90},
        {"nome": "Premium", "descricao": "Acesso à musculação e aulas em horário integral", "valor_mensal": 149.90},
        {"nome": "VIP", "descricao": "Acesso completo à academia com personal trainer", "valor_mensal": 299.90},
    ]
    
    for plano_data in planos:
        plano = db.query(Plano).filter(Plano.nome == plano_data["nome"]).first()
        if not plano:
            plano = Plano(**plano_data)
            db.add(plano)
    
    db.commit()
    return db.query(Plano).all()


def gerar_nome_aleatorio():
    """
    Gera um nome aleatório para os alunos.
    """
    nomes = ["Ana", "João", "Maria", "Pedro", "Lucas", "Mariana", "Carlos", "Julia", 
             "Felipe", "Beatriz", "Rafael", "Laura", "Guilherme", "Gabriela", "Thiago", 
             "Amanda", "Bruno", "Larissa", "Leonardo", "Isabela", "Diego", "Natália",
             "Vitor", "Carolina", "Matheus", "Camila", "Gustavo", "Eduarda", "Rodrigo",
             "Manuela", "André", "Sophia", "Ricardo", "Luiza", "Eduardo", "Helena",
             "Leandro", "Júlia", "Daniel", "Valentina", "Marcelo", "Letícia", "Paulo",
             "Isabella", "Henrique", "Alice", "Miguel", "Clara", "Samuel", "Yasmin"]
    
    sobrenomes = ["Silva", "Santos", "Oliveira", "Souza", "Pereira", "Costa", "Rodrigues", 
                  "Almeida", "Nascimento", "Lima", "Araújo", "Fernandes", "Carvalho", "Gomes", 
                  "Martins", "Rocha", "Ribeiro", "Alves", "Monteiro", "Mendes", "Barros", 
                  "Freitas", "Barbosa", "Nunes", "Cardoso", "Moreira", "Vieira", "Dias", 
                  "Castro", "Campos", "Bezerra", "Correia", "Andrade", "Ferreira", "Teixeira"]
    
    return f"{random.choice(nomes)} {random.choice(sobrenomes)}"


def gerar_email(nome):
    """
    Gera um email baseado no nome do aluno.
    """
    nome = nome.lower().replace(" ", ".")
    dominio = random.choice(["gmail.com", "hotmail.com", "yahoo.com", "outlook.com", "protonmail.com"])
    return f"{nome}@{dominio}"


def gerar_telefone():
    """
    Gera um número de telefone aleatório.
    """
    ddd = random.randint(11, 99)
    numero1 = random.randint(90000, 99999)
    numero2 = random.randint(0000, 9999)
    return f"({ddd}) 9{numero1}-{numero2}"


def criar_alunos_teste(db: Session, num_alunos=100):
    """
    Cria alunos para teste com perfis variados para treinar o modelo de churn.
    """
    # Obter os planos
    planos = db.query(Plano).all()
    
    alunos_criados = []
    
    # Definir perfis para predição de churn
    perfis = [
        {
            "nome": "Aluno Fiel",
            "desc": "Frequência alta (3-5x/semana), longa duração (60-120min), plano Premium/VIP",
            "visitas_semana": (2.5, 5),  # Reduzido o mínimo para aumentar sobreposição
            "duracao": (50, 120),  # Reduzido o mínimo para aumentar sobreposição
            "planos_preferenciais": [0, 1, 2],  # Agora todos os planos para aumentar sobreposição
            "prob_ativo": 0.90,  # Reduzido de 0.95
            "porcentagem": 0.25  # 25% dos alunos
        },
        {
            "nome": "Aluno Regular",
            "desc": "Frequência média (2-4x/semana), duração média (45-90min), qualquer plano",
            "visitas_semana": (1.5, 4),  # Reduzido o mínimo para aumentar sobreposição
            "duracao": (40, 90),  # Reduzido o mínimo para aumentar sobreposição
            "planos_preferenciais": [0, 1, 2],  # Qualquer plano
            "prob_ativo": 0.80,  # Reduzido de 0.85
            "porcentagem": 0.35  # 35% dos alunos
        },
        {
            "nome": "Aluno Casual",
            "desc": "Frequência baixa (1-3x/semana), duração média (30-60min), plano Básico",
            "visitas_semana": (0.8, 3),  # Reduzido o mínimo para aumentar sobreposição
            "duracao": (25, 65),  # Aumentado o máximo para sobreposição
            "planos_preferenciais": [0, 1],  # Agora também Premium para sobreposição
            "prob_ativo": 0.60,  # Reduzido de 0.65
            "porcentagem": 0.20  # 20% dos alunos
        },
        {
            "nome": "Aluno em Risco",
            "desc": "Frequência muito baixa (0-1x/semana), curta duração (15-45min), plano Básico",
            "visitas_semana": (0, 1.2),  # Aumentado o máximo para sobreposição
            "duracao": (15, 50),  # Aumentado o máximo para sobreposição
            "planos_preferenciais": [0, 1],  # Agora também Premium para sobreposição
            "prob_ativo": 0.35,  # Aumentado de 0.30 para mais sobreposição
            "porcentagem": 0.15  # 15% dos alunos
        },
        {
            "nome": "Aluno Desistente",
            "desc": "Sem visitas recentes, historicamente baixa frequência, qualquer plano",
            "visitas_semana": (0, 0.8),  # Aumentado o máximo para sobreposição
            "duracao": (10, 40),  # Aumentado o máximo para sobreposição
            "planos_preferenciais": [0, 1, 2],  # Qualquer plano
            "prob_ativo": 0.10,  # Aumentado de 0.05 para mais sobreposição
            "porcentagem": 0.05  # 5% dos alunos
        }
    ]
    
    # Distribuir quantidades por perfil
    distribuicao = {}
    alunos_restantes = num_alunos
    
    for i, perfil in enumerate(perfis):
        if i == len(perfis) - 1:
            # Último perfil recebe o restante
            distribuicao[i] = alunos_restantes
        else:
            quantidade = round(num_alunos * perfil["porcentagem"])
            distribuicao[i] = quantidade
            alunos_restantes -= quantidade
    
    print(f"Distribuição de alunos por perfil:")
    for i, perfil in enumerate(perfis):
        print(f"  - {perfil['nome']}: {distribuicao[i]} alunos")
    
    # Data atual para referência
    agora = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Criar alunos por perfil
    for perfil_id, quantidade in distribuicao.items():
        perfil = perfis[perfil_id]
        
        for _ in range(quantidade):
            nome = gerar_nome_aleatorio()
            email = gerar_email(nome)
            
            # Verificar se o email já existe
            while db.query(Aluno).filter(Aluno.email == email).first():
                nome = gerar_nome_aleatorio()
                email = gerar_email(nome)
            
            # Gerar data de nascimento (18-60 anos)
            anos = random.randint(18, 60)
            dias = random.randint(1, 365)
            data_nascimento = agora - datetime.timedelta(days=anos*365 + dias)
            
            # CORREÇÃO: Gerar data de inscrição explicitamente no passado (30-365 dias atrás)
            # Mais antigo para perfis fiéis, mais recente para perfis em risco/desistentes
            min_dias = 30 + (180 * (1 - perfil_id / (len(perfis) - 1)))  # 210 dias para aluno fiel, 30 para desistente
            max_dias = 180 + (185 * (1 - perfil_id / (len(perfis) - 1)))  # 365 dias para aluno fiel, 180 para desistente
            dias_inscricao = random.randint(int(min_dias), int(max_dias))
            data_inscricao = agora - datetime.timedelta(days=dias_inscricao)
            
            # Adicionar chance de exceção para aumentar sobreposição entre perfis
            # 10% de chance de comportamento atípico
            if random.random() < 0.10:
                # Randomizar data de inscrição fora do padrão do perfil
                dias_inscricao = random.randint(30, 365)
                data_inscricao = agora - datetime.timedelta(days=dias_inscricao)
            
            # Determinar se o aluno está ativo com base no perfil
            # Adicionar ruído para aumentar a sobreposição entre perfis
            chance_ativo = perfil["prob_ativo"]
            
            # Adicionar ruído à probabilidade (±10%)
            chance_ativo = min(1.0, max(0.0, chance_ativo * random.uniform(0.9, 1.1)))
            
            ativo = 1 if random.random() < chance_ativo else 0
            
            # Uma pequena chance (5%) de inverter o status para criar mais ruído
            if random.random() < 0.05:
                ativo = 1 - ativo  # Inverte o status
            
            # Se o aluno está inativo, a data de inscrição deve ser mais antiga
            if not ativo:
                data_inscricao = data_inscricao - datetime.timedelta(days=random.randint(30, 90))
            
            # Selecionar plano com base nas preferências do perfil
            plano_idx = random.choice(perfil["planos_preferenciais"])
            plano_id = planos[plano_idx].id
            
            aluno_data = {
                "nome": nome,
                "email": email,
                "telefone": gerar_telefone(),
                "data_nascimento": data_nascimento,
                "data_inscricao": data_inscricao,
                "ativo": ativo,
                "plano_id": plano_id
            }
            
            aluno = Aluno(**aluno_data)
            db.add(aluno)
            db.flush()  # Para obter o ID
            
            # Adicionar o perfil como atributo para criar check-ins coerentes
            aluno.perfil = perfil
            alunos_criados.append(aluno)
    
    db.commit()
    return alunos_criados


def criar_checkins_teste(db: Session, alunos):
    """
    Cria checkins para os alunos com padrões baseados nos perfis.
    """
    # Data atual
    agora = datetime.datetime.now()
    
    print(f"Criando checkins para {len(alunos)} alunos...")
    
    # Criar checkins para cada aluno
    for aluno in alunos:
        # Obter o perfil do aluno
        perfil = aluno.perfil
        
        # CORREÇÃO: Garantir que usamos a data de inscrição correta
        data_inscricao = aluno.data_inscricao
        
        # Calcular número de dias desde a inscrição até hoje (sempre positivo)
        dias_desde_inscricao = (agora - data_inscricao).days
        
        if dias_desde_inscricao <= 0:
            print(f"AVISO: Aluno {aluno.id} tem data de inscrição no futuro. Ajustando para 1 dia atrás.")
            dias_desde_inscricao = 1
            data_inscricao = agora - datetime.timedelta(days=1)
        
        # Calcular número de visitas esperadas (considerando os alunos ativos)
        if aluno.ativo == 1:
            # Alunos ativos mantêm a frequência de visitas de acordo com seu perfil
            visitas_por_semana = random.uniform(*perfil["visitas_semana"])
            
            # Adicionar ruído às visitas por semana (±20%)
            visitas_por_semana = visitas_por_semana * random.uniform(0.8, 1.2)
            
            # Garantir que média de visitas dos alunos ativos seja em torno de 3/semana
            if perfil["nome"] == "Aluno em Risco" or perfil["nome"] == "Aluno Desistente":
                # Mesmo para perfis de risco, alunos que permaneceram ativos têm mais visitas
                # Reduzir o mínimo para mais sobreposição
                visitas_por_semana = max(visitas_por_semana, random.uniform(1.0, 2.5))
                
            # 10% de chance de comportamento atípico para ativos (muito poucas visitas)
            if random.random() < 0.10:
                visitas_por_semana = random.uniform(0.2, 1.0)
        else:
            # Alunos inativos têm menos visitas que o esperado para seu perfil
            # A frequência de inativos será sempre menor que 2 visitas por semana
            visitas_por_semana = random.uniform(0, min(2.0, perfil["visitas_semana"][0]))
            
            # 10% de chance de comportamento atípico para inativos (muitas visitas)
            if random.random() < 0.10:
                visitas_por_semana = random.uniform(2.0, 4.0)
        
        # Calcular número total de visitas
        num_visitas = int((dias_desde_inscricao / 7) * visitas_por_semana)
        
        # Variar número de visitas (±20%) para adicionar mais aleatoriedade
        variacao = random.uniform(0.8, 1.2)
        num_visitas = int(num_visitas * variacao)
        
        # Limitar o número máximo de visitas para evitar muitos dados
        num_visitas = min(num_visitas, 150)
        
        # Para alunos desistentes, garantir poucas ou nenhuma visita recente
        if aluno.ativo == 0 or perfil["nome"] == "Aluno Desistente":
            # Período sem visitas (últimos 20-80 dias para mais sobreposição)
            periodo_sem_visitas = random.randint(20, 80)
            
            # 15% de chance de ter visitas recentes mesmo sendo inativo (ruído)
            if random.random() < 0.15:
                periodo_sem_visitas = random.randint(0, 10)
        else:
            # Alunos ativos podem ter períodos sem visitas mais curtos (0-14 dias)
            periodo_sem_visitas = random.randint(0, 14)
            
            # 15% de chance de ter longo período sem visitas mesmo sendo ativo (ruído)
            if random.random() < 0.15:
                periodo_sem_visitas = random.randint(25, 45)
            
            # Alunos em risco tendem a ter períodos sem visitas mais longos
            if perfil["nome"] == "Aluno em Risco":
                periodo_sem_visitas = random.randint(7, 30)
        
        print(f"Aluno {aluno.id} ({aluno.nome}) - Perfil: {perfil['nome']} - Visitas: {num_visitas} - Período sem visitas: {periodo_sem_visitas} dias")
        
        # CORREÇÃO: Criar lista de dias possíveis para checkins, entre a data de inscrição e hoje
        # Excluindo o período sem visitas
        dias_possiveis = list(range(periodo_sem_visitas, dias_desde_inscricao))
        
        # Se não houver dias possíveis ou número de visitas for 0, continue
        if not dias_possiveis or num_visitas == 0:
            continue
        
        # Selecionar dias aleatórios para visitas
        dias_visitados = sorted(random.sample(dias_possiveis, min(num_visitas, len(dias_possiveis))))
        
        # Padrão de visitas (dias da semana, horários)
        dias_semana_prefer = None  # Sem preferência inicial
        hora_prefer = None  # Sem preferência inicial
        
        # Alunos regulares tendem a manter padrões consistentes
        if perfil["nome"] in ["Aluno Fiel", "Aluno Regular"]:
            # Preferência por dias da semana (ex: seg, qua, sex ou ter, qui, sáb)
            if random.random() < 0.6:  # Reduzido para 60% (era 70%)
                dias_semana_prefer = random.sample(range(7), random.randint(3, 5))
                
            # Preferência por horário (ex: sempre de manhã ou sempre à noite)
            if random.random() < 0.7:  # Reduzido para 70% (era 80%)
                if random.random() < 0.4:  # 40% preferem de manhã
                    hora_prefer = (6, 10)
                elif random.random() < 0.7:  # 30% preferem fim da tarde
                    hora_prefer = (17, 20)
                else:  # 30% preferem o meio do dia
                    hora_prefer = (11, 16)
        
        # Criar checkins para os dias selecionados
        for dias_atras in dias_visitados:
            # CORREÇÃO: Garantir que checkins estão entre a data de inscrição e hoje
            data_entrada = agora - datetime.timedelta(days=dias_atras)
            
            # VERIFICAÇÃO: Se o check-in é anterior à inscrição, pular
            if data_entrada < data_inscricao:
                continue
            
            # Ajustar dia da semana se houver preferência
            if dias_semana_prefer and data_entrada.weekday() not in dias_semana_prefer:
                # Chances de ainda ir em um dia não preferido
                if random.random() > 0.4:  # Aumentado para 40% (era 30%)
                    continue
            
            # Horário de entrada respeitando preferências se houver
            if hora_prefer:
                hora = random.randint(hora_prefer[0], hora_prefer[1])
                # Pequena variação em torno do horário preferido
                if random.random() > 0.7:  # Aumentado para 30% (era 20%)
                    hora = random.randint(6, 22)
            else:
                hora = random.randint(6, 22)
            
            minuto = random.randint(0, 59)
            
            data_entrada = data_entrada.replace(hour=hora, minute=minuto, second=0, microsecond=0)
            
            # Duração da visita baseada no perfil
            duracao_minutos = random.randint(*perfil["duracao"])
            
            # Adicionar maior variação na duração (±25%)
            variacao = random.uniform(0.75, 1.25)
            duracao_minutos = int(duracao_minutos * variacao)
            
            data_saida = data_entrada + datetime.timedelta(minutes=duracao_minutos)
            
            # VERIFICAÇÃO: Garantir que o check-in é depois da inscrição e antes de agora
            if data_entrada < data_inscricao or data_entrada > agora:
                continue
                
            # Criar checkin
            checkin = Checkin(
                aluno_id=aluno.id,
                data_entrada=data_entrada,
                data_saida=data_saida,
                duracao_minutos=duracao_minutos
            )
            db.add(checkin)
    
    db.commit()


def inicializar_banco(num_alunos=100):
    """
    Inicializa o banco de dados com dados para treinamento do modelo de churn.
    """
    print("Criando tabelas no banco de dados...")
    Base.metadata.create_all(bind=engine)
    
    # Criar sessão
    db = SessionLocal()
    
    try:
        print("Criando planos básicos...")
        planos = criar_planos(db)
        print(f"Criados {len(planos)} planos")
        
        print(f"Criando {num_alunos} alunos para treinar o modelo de churn...")
        alunos = criar_alunos_teste(db, num_alunos)
        print(f"Criados {len(alunos)} alunos")
        
        print("Criando checkins com padrões específicos para cada perfil de aluno...")
        criar_checkins_teste(db, alunos)
        
        print("Banco de dados inicializado com sucesso para modelagem de churn!")
        
        # CORREÇÃO: Exibir estatísticas mais detalhadas para verificação
        alunos_ativos = db.query(Aluno).filter(Aluno.ativo == 1).all()
        alunos_inativos = db.query(Aluno).filter(Aluno.ativo == 0).all()
        total_checkins = db.query(Checkin).count()
        
        print(f"\nEstatísticas dos dados:")
        print(f"  - Total de alunos: {len(alunos)}")
        print(f"  - Alunos ativos: {len(alunos_ativos)} ({len(alunos_ativos)/len(alunos)*100:.1f}%)")
        print(f"  - Alunos inativos: {len(alunos_inativos)} ({len(alunos_inativos)/len(alunos)*100:.1f}%)")
        print(f"  - Total de check-ins: {total_checkins}")
        print(f"  - Média de check-ins por aluno: {total_checkins/len(alunos):.1f}")
        
        # Verificar datas de inscrição
        data_atual = datetime.datetime.now()
        futuro_count = 0
        for aluno in alunos:
            if aluno.data_inscricao > data_atual:
                futuro_count += 1
        
        if futuro_count > 0:
            print(f"\nALERTA: {futuro_count} alunos têm datas de inscrição no futuro!")
        else:
            print("\nTodas as datas de inscrição estão no passado (correto).")
        
        # Calcular médias de check-ins por semana
        print("\nMédia de check-ins por semana:")
        for tipo, lista_alunos in [("Ativos", alunos_ativos), ("Inativos", alunos_inativos)]:
            total_visitas = 0
            total_semanas = 0
            
            for aluno in lista_alunos:
                # Contar check-ins deste aluno
                checkins = db.query(Checkin).filter(Checkin.aluno_id == aluno.id).count()
                # Calcular semanas desde inscrição
                semanas = abs((data_atual - aluno.data_inscricao).days) / 7
                if semanas > 0:
                    total_visitas += checkins
                    total_semanas += semanas
            
            if total_semanas > 0:
                media = total_visitas / total_semanas
                print(f"  - Alunos {tipo}: {media:.2f} visitas/semana")
            else:
                print(f"  - Alunos {tipo}: Sem dados suficientes")
        
    except Exception as e:
        print(f"Erro ao inicializar banco de dados: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Padrão é 100 alunos, mas pode ser ajustado
    num_alunos = 100
    if len(sys.argv) > 1:
        try:
            num_alunos = int(sys.argv[1])
        except:
            pass
    
    # Tentar limpar as tabelas antes de recriar
    try:
        print("Limpando tabelas existentes...")
        db = SessionLocal()
        db.execute("DELETE FROM checkins")
        db.execute("DELETE FROM alunos")
        db.commit()
        db.close()
        print("Tabelas limpas com sucesso.")
    except Exception as e:
        print(f"Aviso: Não foi possível limpar as tabelas. Erro: {e}")
    
    inicializar_banco(num_alunos) 