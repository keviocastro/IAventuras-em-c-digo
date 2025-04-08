from datetime import datetime, timedelta
import random
import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import text  # Adicione esta importação no topo do arquivo

sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent))

from models.database import engine
from models.entities import Aluno, CheckIn, Plano
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

new_data = pd.read_csv(Path(__file__).parent.parent / "data" / "MOCK_DATA.csv")

# criar uma sessão com o banco de dados
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()


def limpar_tabela_alunos(db: Session):
    """
    Remove todos os registros da tabela de alunos
    """
    try:
        # Limpar planos primeiro (se necessário)
        db.query(Plano).delete()

        # Remover todos os check-ins primeiro (devido à restrição de chave estrangeira)
        db.query(CheckIn).delete()

        # Depois remover todos os alunos
        db.query(Aluno).delete()

        db.commit()
        print("Tabela de alunos e check-ins limpa com sucesso!")
        return True
    except Exception as e:
        db.rollback()
        print(f"Erro ao limpar tabela de alunos: {str(e)}")
        return False


def inserir_alunos_unicos(new_data: pd.DataFrame, db: Session):
    """
    Insere apenas alunos únicos no banco de dados
    """
    try:
        # Extrair alunos únicos do DataFrame
        alunos_unicos = new_data[
            ["aluno_id", "aluno_status", "plano_nome", "plano_id"]
        ].drop_duplicates(subset=["aluno_id"])

        print(f"Inserindo {len(alunos_unicos)} alunos únicos...")

        # Inserir cada aluno único
        for _, row in alunos_unicos.iterrows():
            # Mapear o plano_nome para plano_id se necessário
            plano_id = row["plano_id"]

            # Obter o ID do aluno
            aluno_id = row["aluno_id"]

            # Obter o status do aluno
            aluno_status = (
                row["aluno_status"] if "aluno_status" in row else "inativo"
            )

            # Inserir novo aluno no banco de dados
            novo_aluno = Aluno(
                id=aluno_id,
                aluno_status=aluno_status,
                plano_id=plano_id,
            )
            db.add(novo_aluno)

        # Fazer commit dos alunos
        db.commit()
        print(f"Alunos inseridos com sucesso! ({len(alunos_unicos)} alunos)")
        return True

    except Exception as e:
        db.rollback()
        print(f"Erro na inserção de alunos: {str(e)}")
        return False


def inserir_checkins(new_data: pd.DataFrame, db: Session):
    """
    Insere os check-ins no banco de dados
    """
    try:
        # Inserir check-ins
        checkins_count = 0
        for _, row in new_data.iterrows():
            # Se tiver data de entrada e aluno_id, criar check-in
            if pd.notna(row.get("data_entrada", None)) and pd.notna(
                row.get("aluno_id", None)
            ):
                aluno_id = row["aluno_id"]
                data_entrada = pd.to_datetime(row["data_entrada"])
                duracao_treino = (
                    row["duracao_treino"]
                    if pd.notna(row.get("duracao_treino", None))
                    else None
                )

                # Criar o check-in
                novo_checkin = CheckIn(
                    aluno_id=aluno_id,
                    data_entrada=data_entrada,
                    duracao_treino=duracao_treino,
                )
                db.add(novo_checkin)
                checkins_count += 1

                # Fazer commit a cada 100 registros
                if checkins_count % 100 == 0:
                    db.commit()
                    print(f"Inseridos {checkins_count} check-ins...")

        # Fazer commit final
        db.commit()
        print(f"Check-ins inseridos com sucesso! ({checkins_count} check-ins)")
        return True

    except Exception as e:
        db.rollback()
        print(f"Erro na inserção de check-ins: {str(e)}")
        return False


def inicializar_planos(db: Session):
    """
    Insere os planos básicos no banco de dados se eles não existirem
    """
    try:
        # Verificar se já existem planos
        planos_existentes = db.execute(
            text("SELECT COUNT(*) FROM planos")
        ).scalar()

        if planos_existentes == 0:
            # Inserir planos básicos
            db.execute(
                text("""
                INSERT INTO planos (id, plano_nome) VALUES 
                (1, 'Bronze'),
                (2, 'Prata'),
                (3, 'Ouro')
                ON CONFLICT (id) DO NOTHING
            """)
            )
            db.commit()
            print("Planos inicializados com sucesso!")
        else:
            print(
                f"Planos já existem no banco de dados ({planos_existentes} encontrados)."
            )

        return True
    except Exception as e:
        db.rollback()
        print(f"Erro ao inicializar planos: {str(e)}")
        return False


# Função principal que chama as funções acima
def update_db(new_data: pd.DataFrame, db: Session):
    """
    Atualiza os dados no banco de dados com os dados do DataFrame
    """
    try:
        # Passo 1: Inicializar planos básicos
        if inicializar_planos(db):
            # Passo 2: Inserir alunos únicos
            if inserir_alunos_unicos(new_data, db):
                # Passo 3: Inserir check-ins
                inserir_checkins(new_data, db)
            else:
                print(
                    "Falha ao inserir alunos. Não serão inseridos check-ins."
                )
        else:
            print(
                "Falha ao inicializar planos. Não serão inseridos alunos ou check-ins."
            )

    except Exception as e:
        db.rollback()
        print(f"Erro na atualização do banco de dados: {str(e)}")
    finally:
        # Fecha a sessão do banco de dados
        db.close()


def obter_alunos_existentes(db: Session):
    """
    Recupera todos os alunos existentes no banco de dados

    Returns:
        list: Lista contendo objetos Aluno
    """
    try:
        alunos = db.query(Aluno).all()
        print(f"Encontrados {len(alunos)} alunos no banco de dados")
        return alunos
    except Exception as e:
        print(f"Erro ao consultar alunos: {str(e)}")
        return []


def gerar_checkins_simulados(
    db: Session, alunos=None, dias_passados=90, frequencia_base=0.6
):
    """
    Gera dados de check-in simulados para treinamento do modelo de ML

    Args:
        db (Session): Sessão do banco de dados
        alunos (list, optional): Lista de alunos ou None para buscar todos
        dias_passados (int): Quantidade de dias no passado para gerar dados
        frequencia_base (float): Probabilidade base de um aluno fazer check-in em um dia

    Returns:
        dict: Estatísticas sobre os dados gerados
    """
    try:
        # Se não forneceu alunos, busca todos
        if alunos is None:
            alunos = obter_alunos_existentes(db)

        if not alunos:
            print("Não foram encontrados alunos para gerar checkins.")
            return {"status": "error", "message": "Nenhum aluno encontrado"}

        # Data atual e inicial
        data_atual = datetime.now()
        data_inicial = data_atual - timedelta(days=dias_passados)

        print(
            f"Gerando checkins simulados de {data_inicial.date()} até {data_atual.date()}"
        )

        # Contadores para estatísticas
        total_checkins = 0
        alunos_com_checkin = set()

        # Perfis de frequência baseados no plano
        perfis_frequencia = {
            1: frequencia_base * 0.85,  # Bronze - frequência mais baixa
            2: frequencia_base * 1.15,  # Prata - frequência média
            3: frequencia_base * 1.30,  # Ouro - frequência mais alta
        }

        # Padrões de dias da semana (índice 0 = segunda, 6 = domingo)
        padrao_dias_semana = [
            1.2,  # Segunda - mais movimentado após fim de semana
            1.15,  # Terça
            1.1,  # Quarta
            1.05,  # Quinta
            0.95,  # Sexta - menos frequentado
            0.8,  # Sábado - menos frequentado
            0.7,  # Domingo - menos frequentado
        ]

        # Meses com sazonalidade (índice 1 = janeiro, 12 = dezembro)
        sazonalidade_mes = {
            1: 1.3,  # Janeiro - muitas resoluções de ano novo
            2: 1.2,  # Fevereiro - ainda forte
            3: 1.1,  # Março
            4: 1.0,  # Abril
            5: 0.95,  # Maio
            6: 0.9,  # Junho
            7: 0.85,  # Julho - férias, menos movimento
            8: 0.9,  # Agosto
            9: 1.0,  # Setembro - volta às aulas
            10: 1.1,  # Outubro
            11: 1.05,  # Novembro
            12: 0.8,  # Dezembro - festas, menos movimento
        }

        # Feriados (simplificado, em formato 'MM-DD')
        feriados = [
            "01-01",  # Ano Novo
            "04-21",  # Tiradentes
            "05-01",  # Dia do Trabalho
            "09-07",  # Independência
            "10-12",  # Nossa Senhora Aparecida
            "11-02",  # Finados
            "11-15",  # Proclamação da República
            "12-25",  # Natal
        ]

        # Faixas de horário e suas probabilidades
        faixas_horario = [
            (5, 8, 0.25),  # Manhã cedo: 5h-8h (25% dos check-ins)
            (8, 11, 0.15),  # Manhã: 8h-11h (15%)
            (11, 14, 0.10),  # Almoço: 11h-14h (10%)
            (14, 17, 0.10),  # Tarde: 14h-17h (10%)
            (17, 21, 0.35),  # Noite: 17h-21h (35%)
            (21, 23, 0.05),  # Noite tarde: 21h-23h (5%)
        ]

        # Gerar checkins para cada aluno
        for i, aluno in enumerate(alunos):
            # Frequência base de acordo com o plano
            frequencia = perfis_frequencia.get(aluno.plano_id, frequencia_base)

            # Ajustar frequência com base no status (inativos têm menos checkins)
            if aluno.aluno_status == "inativo":
                frequencia *= 0.35

            # Cada aluno tem um padrão individual (variação de ±15%)
            variacao_individual = 0.85 + (
                random.random() * 0.3
            )  # Entre 0.85 e 1.15
            frequencia *= variacao_individual

            # Padrão de horário preferido do aluno (escolhe uma faixa com maior probabilidade)
            faixa_preferida = random.choices(
                range(len(faixas_horario)),
                weights=[f[2] for f in faixas_horario],
                k=1,
            )[0]

            # Dias consecutivos máximos que este aluno normalmente treina
            max_dias_consecutivos = random.choice([2, 3, 4, 5])
            dias_consecutivos_atual = 0

            # Dias de descanso típicos após sequência de treinos
            dias_descanso_tipico = random.choice([1, 1, 2, 2, 3])
            dias_sem_treino = 0

            # Padrão de treino: alguns dias específicos da semana
            dias_preferenciais = random.sample(
                range(7), k=random.randint(3, 5)
            )
            usa_dias_preferenciais = (
                random.random() < 0.7
            )  # 70% dos alunos seguem dias específicos

            # Para cada dia no período
            data_corrente = data_inicial
            # ultimo_checkin = None
            checkins_do_aluno = 0

            while data_corrente <= data_atual:
                # Verificar se é feriado
                data_mes_dia = data_corrente.strftime("%m-%d")
                eh_feriado = data_mes_dia in feriados

                # Ajustes de probabilidade baseados em dia da semana e mês
                dia_semana = (
                    data_corrente.weekday()
                )  # 0 = segunda, 6 = domingo
                multiplicador_dia = padrao_dias_semana[dia_semana]
                multiplicador_mes = sazonalidade_mes.get(
                    data_corrente.month, 1.0
                )

                # Reduzir probabilidade em feriados
                multiplicador_feriado = 0.3 if eh_feriado else 1.0

                # Analisar padrão de dias consecutivos
                if dias_consecutivos_atual >= max_dias_consecutivos:
                    # Forçar descanso após vários dias consecutivos
                    probabilidade_checkin = (
                        0.05  # Muito baixa, quase certeza de descanso
                    )
                    if random.random() > probabilidade_checkin:
                        dias_consecutivos_atual = 0
                        dias_sem_treino += 1
                        data_corrente += timedelta(days=1)
                        continue

                # Verificar se segue padrão de dias preferenciais
                if (
                    usa_dias_preferenciais
                    and dia_semana not in dias_preferenciais
                ):
                    probabilidade_checkin = (
                        frequencia * 0.2
                    )  # Baixa probabilidade fora dos dias preferidos
                else:
                    # Probabilidade base ajustada por todos os fatores
                    probabilidade_checkin = (
                        frequencia
                        * multiplicador_dia
                        * multiplicador_mes
                        * multiplicador_feriado
                    )

                # Ajustar após descanso (mais provável voltar após alguns dias de descanso)
                if dias_sem_treino >= dias_descanso_tipico:
                    probabilidade_checkin *= 1.5

                # Chance do aluno fazer check-in neste dia
                if random.random() < probabilidade_checkin:
                    # Determinar a faixa de horário
                    pesos_faixa = []
                    for idx, _ in enumerate(faixas_horario):
                        if idx == faixa_preferida:
                            pesos_faixa.append(
                                0.7
                            )  # 70% de chance para faixa preferida
                        else:
                            pesos_faixa.append(
                                0.3 / (len(faixas_horario) - 1)
                            )  # Restante distribuído

                    faixa_escolhida = random.choices(
                        range(len(faixas_horario)), weights=pesos_faixa, k=1
                    )[0]
                    hora_inicio, hora_fim, _ = faixas_horario[faixa_escolhida]

                    # Distribuição não uniforme dentro da faixa para ser mais realista
                    meio_faixa = (hora_inicio + hora_fim) / 2

                    # Gerar hora com distribuição concentrada nos horários de pico
                    hora_decimal = random.triangular(
                        hora_inicio, hora_fim, meio_faixa
                    )
                    hora = int(hora_decimal)
                    minuto = int((hora_decimal - hora) * 60)

                    # Data e hora do check-in
                    data_checkin = data_corrente.replace(
                        hour=hora, minute=minuto
                    )

                    # Duração do treino baseada no horário do dia e perfil do aluno
                    if (
                        hora_inicio >= 17
                    ):  # Final da tarde/noite - treinos mais longos
                        duracao_base = random.triangular(45, 90, 65)
                    elif hora_inicio <= 8:  # Manhã cedo - treinos moderados
                        duracao_base = random.triangular(40, 70, 55)
                    else:  # Durante o dia - treinos mais curtos por causa da rotina
                        duracao_base = random.triangular(30, 60, 45)

                    # Ajustar duração pelo plano (alunos premium tendem a treinar mais)
                    multiplicador_duracao = {
                        1: 0.9,  # Bronze - treinos mais curtos
                        2: 1.0,  # Prata - duração média
                        3: 1.15,  # Ouro - treinos mais longos
                    }.get(aluno.plano_id, 1.0)

                    # Duração final com pequena variação aleatória
                    duracao = int(duracao_base * multiplicador_duracao)

                    # Garantir limites razoáveis
                    duracao = max(20, min(duracao, 120))

                    # Criar o check-in
                    novo_checkin = CheckIn(
                        aluno_id=aluno.id,
                        data_entrada=data_checkin,
                        duracao_treino=duracao,
                    )
                    db.add(novo_checkin)
                    total_checkins += 1
                    alunos_com_checkin.add(aluno.id)
                    checkins_do_aluno += 1

                    # Commit a cada 100 registros para melhor performance
                    if total_checkins % 100 == 0:
                        db.commit()
                        print(
                            f"Inseridos {total_checkins} checkins até agora..."
                        )

                    # Atualizar contadores
                    # ultimo_checkin = data_checkin
                    dias_consecutivos_atual += 1
                    dias_sem_treino = 0
                else:
                    # Não fez check-in neste dia
                    dias_consecutivos_atual = 0
                    dias_sem_treino += 1

                # Próximo dia
                data_corrente += timedelta(days=1)

            # Para alunos inativos, modelar padrão realista de abandono
            if aluno.aluno_status == "inativo" and checkins_do_aluno > 0:
                # Determinar quando começou o processo de abandono
                dias_abandono = random.randint(30, min(60, dias_passados - 10))
                data_inicio_abandono = data_atual - timedelta(
                    days=dias_abandono
                )

                # Último check-in deve ser anterior à data de abandono
                dias_ultimo_checkin = random.randint(
                    dias_abandono - 20, dias_abandono - 5
                )
                data_ultimo_checkin = data_atual - timedelta(
                    days=dias_ultimo_checkin
                )

                # Fase de redução de frequência antes do abandono completo
                data_corrente = data_inicio_abandono
                num_checkins_abandono = random.randint(2, 5)

                for _ in range(num_checkins_abandono):
                    if data_corrente >= data_ultimo_checkin:
                        break

                    # Espaçamento cada vez maior entre check-ins
                    dias_espera = random.randint(5, 12)
                    data_corrente += timedelta(days=dias_espera)

                    if (
                        data_corrente > data_ultimo_checkin
                        or data_corrente < data_inicial
                    ):
                        continue

                    hora = random.randint(8, 20)
                    minuto = random.randint(0, 59)

                    # Duração de treino mais curta, típico de quem está perdendo interesse
                    duracao = random.randint(20, 40)

                    # Data e hora do check-in
                    data_checkin = data_corrente.replace(
                        hour=hora, minute=minuto
                    )

                    # Criar o check-in
                    novo_checkin = CheckIn(
                        aluno_id=aluno.id,
                        data_entrada=data_checkin,
                        duracao_treino=duracao,
                    )
                    db.add(novo_checkin)
                    total_checkins += 1

                # Um último check-in claramente mostrando abandono
                if data_ultimo_checkin > data_inicial:
                    hora = random.randint(8, 20)
                    minuto = random.randint(0, 59)

                    data_checkin = data_ultimo_checkin.replace(
                        hour=hora, minute=minuto
                    )

                    # Duração do treino muito curto, indicando falta de comprometimento
                    duracao = random.randint(15, 30)

                    novo_checkin = CheckIn(
                        aluno_id=aluno.id,
                        data_entrada=data_checkin,
                        duracao_treino=duracao,
                    )
                    db.add(novo_checkin)
                    total_checkins += 1

        # Commit final
        db.commit()

        # Estatísticas sobre os dados gerados
        stats = {
            "status": "success",
            "total_checkins": total_checkins,
            "alunos_com_checkin": len(alunos_com_checkin),
            "periodo": f"{data_inicial.date()} a {data_atual.date()}",
            "media_checkins_por_aluno": total_checkins / len(alunos)
            if alunos
            else 0,
        }

        print("Geração de checkins concluída!")
        print(f"Total de checkins: {total_checkins}")
        print(f"Alunos com pelo menos um checkin: {len(alunos_com_checkin)}")

        return stats
    except Exception as e:
        print(f"Erro ao gerar checkins simulados: {str(e)}")
        db.rollback()
        return {"status": "error", "message": str(e)}


# # Executar a atualização
# if __name__ == "__main__":
#     print(f"Colunas disponíveis no DataFrame: {list(new_data.columns)}")

#     # Verificar se o DataFrame tem as colunas necessárias ou possíveis de mapear
#     has_aluno_id = "aluno_id" in new_data.columns
#     has_plano_info = (
#         "plano_id" in new_data.columns or "plano_nome" in new_data.columns
#     )

#     if not has_aluno_id:
#         print(
#             "Aviso: Coluna 'aluno_id' não encontrada. Será usado o índice + 1 como ID."
#         )

#     if not has_plano_info:
#         print(
#             "Erro: Nem 'plano_id' nem 'plano_nome' foram encontrados no DataFrame."
#         )
#         print(f"Colunas disponíveis: {list(new_data.columns)}")
#     else:
#         # Inicializar planos primeiro
#         if inicializar_planos(db):
#             # Limpar tabelas depois de garantir que planos existem
#             if limpar_tabela_alunos(db):
#                 update_db(new_data, db)
#             else:
#                 print(
#                     "Abortando operação devido a erro na limpeza das tabelas."
#                 )
#         else:
#             print(
#                 "Abortando operação devido a erro na inicialização dos planos."
#             )


if __name__ == "__main__":
    # Abrir conexão com o banco
    db = SessionLocal()

    try:
        # Obter alunos existentes
        alunos = obter_alunos_existentes(db)

        dias = 90
        frequencia = 0.64

        # Gerar dados
        stats = gerar_checkins_simulados(db, alunos, dias, frequencia)

        if stats["status"] == "success":
            print(
                f"Check-ins simulados gerados com sucesso! "
                f"Total de check-ins: {stats['total_checkins']} "
                f"(alunos com check-in: {stats['alunos_com_checkin']})"
            )

    finally:
        # Fechar conexão
        db.close()
