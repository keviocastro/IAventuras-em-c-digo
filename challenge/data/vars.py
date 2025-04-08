# Colunas disponíveis no dataset
RAW_COLS = [
    "aluno_id",
    "aluno_status",
    "plano_id",
    "plano_nome",
    "checkin_id",
    "data_entrada",
    "duracao_treino",
]

DATE_COLS = ["checkin_data_entrada"]

ML_COLS = [
    "frequencia_semanal",
    "dias_desde_ultimo_checkin",
    "tempo_medio_na_academia",
    "plano_id",
]

TARGET_COLS = ["aluno_status"]
