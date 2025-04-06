from fastapi import Path
import pandas as pd
from utils.db.crud import PostgreSQLDatabase
from config.project_constants import EnvVars

env = EnvVars()
db_password = env.get_var("DB_PASSWORD")

db = PostgreSQLDatabase(
    user="juanml",
    dbname="churnml",
    password=db_password,
    host="localhost",
    port="5432"
)

def get_model_features(id: int = Path(..., description="ID do aluno")):
    if not db.connect_db():
        return None
    
    check_query = "SELECT id_aluno FROM alunos WHERE id_aluno = %s" # primeiro verifica se o aluno existe no banco de dados
    db.cursor.execute(check_query, (id,))
    if not db.cursor.fetchone():
        db.close_db()
        return None
    
    query = """
    SELECT
        a.id_aluno,
        a.nome_aluno,
        p.nome_plano,
        ci.data_checkin,
        co.data_checkout,
        m.data_inicio,
        m.data_fim
    FROM alunos a
    LEFT JOIN matriculas m ON a.id_aluno = m.id_aluno
    LEFT JOIN planos p ON m.id_plano = p.id_plano
    LEFT JOIN checkins ci ON a.id_aluno = ci.id_aluno
    LEFT JOIN checkouts co ON a.id_aluno = co.id_aluno
        AND co.data_checkout > ci.data_checkin
        AND co.data_checkout = (
            SELECT MIN(co2.data_checkout) 
            FROM checkouts co2 
            WHERE co2.id_aluno = ci.id_aluno 
            AND co2.data_checkout > ci.data_checkin
        )
    WHERE a.id_aluno = %s
    """
    db.cursor.execute(query, (id,))
    rows = db.cursor.fetchall()
    colunas = [desc[0] for desc in db.cursor.description]
    db.close_db()
    
    if not rows:
        return None
    
    df = pd.DataFrame(rows, columns=colunas)
    
    df["data_checkin"] = pd.to_datetime(df["data_checkin"], errors='coerce').dt.tz_localize(None)
    df["data_checkout"] = pd.to_datetime(df["data_checkout"], errors='coerce').dt.tz_localize(None)
    df["data_inicio"] = pd.to_datetime(df["data_inicio"], errors='coerce').dt.tz_localize(None)
    
    now = pd.Timestamp.now().tz_localize(None)
    
    if df["data_checkin"].count() == 0:
        return pd.DataFrame([{
            "frequencia_semanal": 0,
            "tempo_desde_ultimo_checkin": 30,  # valor alto para indicar inatividade
            "duracao_media_visitas": 0,
            "tipo_plano_Mensal": int("mensal" in df["nome_plano"].iloc[0].lower()) if not pd.isna(df["nome_plano"].iloc[0]) else 0,
            "tipo_plano_Semestral": int("semestral" in df["nome_plano"].iloc[0].lower()) if not pd.isna(df["nome_plano"].iloc[0]) else 0
        }])
    
    ultimo_checkin = df["data_checkin"].max()
    data_inicio = df["data_inicio"].min()
    
    if pd.isna(data_inicio):
        data_inicio = df["data_checkin"].min()
    
    dias_ativos = max((ultimo_checkin - data_inicio).days, 1)
    semanas = max(dias_ativos / 7, 1)
    total_checkins = df["data_checkin"].count()
    frequencia_semanal = total_checkins / semanas
    
    tempo_desde_ultimo_checkin = (now - ultimo_checkin).days
    
    df_com_checkout = df.dropna(subset=["data_checkout"])
    
    if len(df_com_checkout) > 0:
        df_com_checkout["duracao_visita"] = (df_com_checkout["data_checkout"] - df_com_checkout["data_checkin"]).dt.total_seconds() / 60
        duracao_media = df_com_checkout["duracao_visita"].mean()
    else:
        duracao_media = 0  # valor padrão se não houver checkouts
    
    plano = ""
    if not pd.isna(df["nome_plano"].iloc[0]):
        plano = df["nome_plano"].iloc[0].lower()
    
    tipo_plano_mensal = int("mensal" in plano)
    tipo_plano_semestral = int("semestral" in plano)
    
    features = pd.DataFrame([{
        "frequencia_semanal": frequencia_semanal,
        "tempo_desde_ultimo_checkin": tempo_desde_ultimo_checkin,
        "duracao_media_visitas": duracao_media,
        "tipo_plano_Mensal": tipo_plano_mensal,
        "tipo_plano_Semestral": tipo_plano_semestral
    }])
    
    return features