import os
import pandas as pd

import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import get_db
from models.entities import Aluno, Plano, CheckIn


def extract_data_to_csv():
    """
    Extrai dados das tabelas Aluno, Plano e CheckIn do banco de dados
    e salva em um arquivo CSV.

    O CSV gerado contém informações combinadas das três entidades,
    possibilitando análise de dados para o modelo de churn.
    """
    try:
        print("Iniciando extração de dados...")

        data_version = "v_1"

        # Obter sessão do banco de dados
        db = next(get_db())

        # Criar lista para armazenar os dados
        dados = []

        # Para cada aluno, buscar suas informações e check-ins
        for checkin in db.query(CheckIn).all():
            aluno = (
                db.query(Aluno).filter(Aluno.id == checkin.aluno_id).first()
            )
            plano = db.query(Plano).filter(Plano.id == aluno.plano_id).first()

            # Adicionar dados à lista
            dados.append(
                {
                    "aluno_id": aluno.id,
                    "aluno_status": aluno.aluno_status,
                    "plano_id": plano.id,
                    "plano_nome": plano.plano_nome,
                    "checkin_id": checkin.id,
                    "checkin_data_entrada": checkin.data_entrada,
                    "checkin_duracao_treino": checkin.duracao_treino,
                }
            )

        # Criar DataFrame pandas
        df = pd.DataFrame(dados)

        # Criar diretório para os arquivos raw_data se não existir
        data_dir = os.path.dirname(os.path.abspath(__file__))
        raw_data_dir = os.path.join(data_dir, "raw_data")
        if not os.path.exists(raw_data_dir):
            os.makedirs(raw_data_dir)

        # Salvar como CSV
        csv_filename = os.path.join(
            raw_data_dir, f"raw_file_{data_version}.csv"
        )
        df.to_csv(csv_filename, index=False)

        print(f"Dados extraídos com sucesso e salvos em: {csv_filename}")
        return csv_filename

    except Exception as e:
        print(f"Erro ao extrair dados: {e}")
        return None


if __name__ == "__main__":
    extract_data_to_csv()
