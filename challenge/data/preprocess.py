import pandas as pd

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from data.vars import DATE_COLS, ML_COLS, TARGET_COLS


# Funções auxiliares para agregação
def mean_interval(dates):
    dates = dates.dropna().sort_values()
    if len(dates) <= 1:
        return 0
    intervals = [
        (dates.iloc[i] - dates.iloc[i - 1]).days for i in range(1, len(dates))
    ]
    return sum(intervals) / len(intervals)


def calculate_weekly_frequency(df, aluno_id):
    """Calcula frequência semanal média baseada nos check-ins"""
    student_data = df[df["aluno_id"] == aluno_id]
    if len(student_data) <= 1:
        return 0

    # Calcula o período total em semanas
    first_checkin = student_data["checkin_data_entrada"].min()
    last_checkin = student_data["checkin_data_entrada"].max()
    total_weeks = max(1, (last_checkin - first_checkin).days / 7)

    return len(student_data) / total_weeks


def mean_duration_minutes(durations):
    valid = durations.dropna()
    return valid.mean() if not valid.empty else 0


def preprocess_data(
    raw_file_path: Path = Path(__file__).parent.parent
    / "data"
    / "raw_data"
    / "raw_file_v_1.csv",
) -> pd.DataFrame:
    """
    Processa dados de alunos e retorna um DataFrame com features para análise.

    Args:
        raw_file_path: Caminho para o arquivo CSV com dados brutos

    Returns:
        DataFrame com features processadas para análise
    """

    # Carrega os dados
    df = pd.read_csv(raw_file_path)
    df = df.drop(columns=["Unnamed: 0"], errors="ignore")

    print(df.columns)

    # Verifica se todas as colunas necessárias existem
    missing_cols = [
        col
        for col in [
            "aluno_id",
            "aluno_status",
            "checkin_data_entrada",
            "checkin_duracao_treino",
        ]
        if col not in df.columns
    ]
    if missing_cols:
        raise ValueError(
            f"Colunas necessárias não encontradas: {missing_cols}"
        )

    # Converte colunas de data para datetime
    for col in DATE_COLS:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.normalize()

    # Converte duracao_treino para minutos se necessário
    if "checkin_duracao_treino" in df.columns:
        # Verifica se já está em minutos ou precisa converter
        if df["checkin_duracao_treino"].dtype == "object":
            df["checkin_duracao_treino"] = (
                pd.to_timedelta(df["checkin_duracao_treino"], errors="coerce")
                .dt.total_seconds()
                .astype(int)
                / 60
            )

    # Remove registros incompletos
    df.dropna(subset=["aluno_id", "checkin_data_entrada"], inplace=True)

    # Calcula frequência semanal para cada aluno
    freq_semanal = {}
    for aluno in df["aluno_id"].unique():
        freq_semanal[aluno] = calculate_weekly_frequency(df, aluno)

    # Agrupa por aluno e calcula features
    alunos = (
        df.groupby("aluno_id")
        .agg(
            aluno_status=("aluno_status", "first"),
            plano_id=("plano_id", "first"),
            ultimo_checkin=("checkin_data_entrada", "max"),
            tempo_medio_na_academia=(
                "checkin_duracao_treino",
                mean_duration_minutes,
            ),
        )
        .reset_index()
    )

    # Adiciona frequência semanal
    alunos["frequencia_semanal"] = (
        alunos["aluno_id"].map(freq_semanal) * 10
    ).astype(int)

    alunos["tempo_medio_na_academia"] = alunos[
        "tempo_medio_na_academia"
    ].astype(int)

    # Encontra a data do checkin mais recente no conjunto de dados
    max_checkin_date = alunos["ultimo_checkin"].max()

    # Calcula dias desde último check-in usando a data máxima como referência
    alunos["dias_desde_ultimo_checkin"] = (
        (max_checkin_date - alunos["ultimo_checkin"])
        .dt.days.fillna(-1)
        .astype(int)
    )

    # Todos os alunos que possuem check-in maior que 50 dias são considerados inativos
    alunos.loc[alunos["dias_desde_ultimo_checkin"] > 50, "aluno_status"] = (
        "inativo"
    )

    # Seleciona 25% dos alunos inativos com check-in recente e muda para ativo
    mask = (alunos["dias_desde_ultimo_checkin"] <= 50) & (
        alunos["aluno_status"] == "inativo"
    )
    sample_indices = alunos[mask].sample(frac=0.25, random_state=42).index
    alunos.loc[sample_indices, "aluno_status"] = "ativo"

    # trocar aluno_status para 1 e 0
    alunos["aluno_status"] = alunos["aluno_status"].map(
        {"ativo": 1, "inativo": 0}
    )

    # Retorna apenas as colunas necessárias
    return alunos[ML_COLS + TARGET_COLS]


if __name__ == "__main__":
    try:
        processed_df = preprocess_data()
        print("Preprocessing successful!")
        print(processed_df.head())
        print("\nInfo:")
        processed_df.info()
        print("\nDescribe:")
        print(processed_df.describe())
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
