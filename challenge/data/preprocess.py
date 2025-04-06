import pandas as pd

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from data.vars import DATE_COLS, ML_COLS


# Funções auxiliares para agregação
def mean_interval(dates):
    dates = dates.dropna().sort_values()
    if len(dates) <= 1:
        return 0
    intervals = [
        (dates.iloc[i] - dates.iloc[i - 1]).days for i in range(1, len(dates))
    ]
    return sum(intervals) / len(intervals)


def mean_duration_minutes(durations):
    valid = durations.dropna()
    return valid.mean().total_seconds() / 60 if not valid.empty else 0


def preprocess_data(
    # raw_file_path: str = "raw_file_v_1.csv"
    raw_file_path: Path = Path(__file__).parent.parent
    / "data"
    / "raw_data"
    / "raw_file_v_1.csv",
) -> pd.DataFrame:
    """
    Processa dados de alunos e retorna um DataFrame com features para análise.

    Args:
        raw_data_dir: Diretório contendo os arquivos de dados
        raw_file: Nome do arquivo CSV com dados dos alunos

    Returns:
        DataFrame com features processadas para análise
    """

    # Carrega os dados usando Path
    df = pd.read_csv(raw_file_path)
    df = df.drop(columns=["Unnamed: 0"], errors="ignore")

    # Define data de referência para cálculos temporais
    now_date = pd.Timestamp.now().normalize()

    # Converte colunas de data para datetime
    date_cols = [col for col in DATE_COLS if col in df.columns]

    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.normalize()

    # Converte colunas numéricas
    df["plano_periodo_contrato"] = pd.to_numeric(
        df["plano_periodo_contrato"], errors="coerce"
    )
    df["plano_valor_mensal"] = pd.to_numeric(
        df["plano_valor_mensal"], errors="coerce"
    )

    # Remove registros incompletos
    df.dropna(
        subset=["aluno_id", "data_cadastro", "checkin_data_entrada"],
        inplace=True,
    )

    # Calcula duração válida de check-in
    if "checkin_duracao" not in df.columns:
        df["duracao_td"] = (
            df["checkin_data_saida"] - df["checkin_data_entrada"]
        )
        df.loc[
            df["duracao_td"].isna() | (df["duracao_td"] < pd.Timedelta(0)),
            "duracao_td",
        ] = pd.NaT
    else:
        # Se já existir duração, converte para timedelta
        df["duracao_td"] = pd.to_timedelta(
            df["checkin_duracao"], errors="coerce"
        )

    # Agrupa por aluno e calcula features
    students = (
        df.groupby("aluno_id")
        .agg(
            data_cadastro=("data_cadastro", "first"),
            status=("status", "first"),
            plano_data_criacao=("plano_data_criacao", "first"),
            plano_periodo_contrato=("plano_periodo_contrato", "first"),
            plano_valor_mensal=("plano_valor_mensal", "first"),
            ultimo_checkin=("checkin_data_entrada", "max"),
            total_checkins=("checkin_data_entrada", "count"),
            media_intervalo_checkins=("checkin_data_entrada", mean_interval),
            tempo_medio_na_academia=("duracao_td", mean_duration_minutes),
        )
        .reset_index()
    )

    # Calcula métricas adicionais
    students["dias_desde_cadastro"] = (
        now_date - students["data_cadastro"]
    ).dt.days
    students["status_aluno"] = (
        students["status"].str.lower().eq("ativo").astype(int)
    )

    # Calcula data de fim do plano - usando plano_data_criacao como data de início
    mask = (
        students["plano_data_criacao"].notna()
        & students["plano_periodo_contrato"].notna()
    )
    students["data_fim_plano"] = pd.NaT
    students.loc[mask, "data_fim_plano"] = students.loc[mask].apply(
        lambda row: row["plano_data_criacao"]
        + pd.DateOffset(months=int(row["plano_periodo_contrato"])),
        axis=1,
    )

    # Calcula dias restantes no plano e dias desde último check-in
    students["vigencia_plano_restante_dias"] = (
        (students["data_fim_plano"] - now_date)
        .dt.days.fillna(0)
        .clip(lower=0)
        .astype(int)
    )

    students["dias_desde_ultimo_checkin"] = (
        (now_date - students["ultimo_checkin"]).dt.days.fillna(-1).astype(int)
    )

    # Usando os nomes corretos para as métricas
    students["valor_plano"] = students["plano_valor_mensal"]
    students["duracao_plano_meses"] = students["plano_periodo_contrato"]

    # Retorna apenas as colunas necessárias
    return students[ML_COLS]


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
