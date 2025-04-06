# Colunas disponíveis no dataset
RAW_COLS = [
    "nome",
    "email",
    "telefone",
    "data_nascimento",
    "sexo",
    "endereco",
    "plano_id",
    "status",
    "data_cadastro",
    "plano_nome",
    "plano_descricao",
    "plano_valor_mensal",
    "plano_periodo_contrato",
    "plano_ativo",
    "plano_data_criacao",
    "checkin_id",
    "checkin_data_entrada",
    "checkin_data_saida",
    "checkin_duracao",
    "checkin_observacao",
]

DATE_COLS = [
    "data_cadastro",
    "plano_data_criacao",
    "checkin_data_entrada",
    "checkin_data_saida",
]

ML_COLS = [
    "aluno_id",
    "dias_desde_cadastro",
    "dias_desde_ultimo_checkin",
    "total_checkins",
    "media_intervalo_checkins",
    "tempo_medio_na_academia",
    "valor_plano",
    "vigencia_plano_restante_dias",
    "status_aluno",
]

TARGET_COLS = [
    "status_aluno",
]
