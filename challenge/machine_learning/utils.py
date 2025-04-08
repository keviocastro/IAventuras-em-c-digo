import csv
import pickle
from datetime import datetime
from pathlib import Path
import random
import numpy as np
import os

import pandas as pd

from eval import evaluate_model


def set_seed(seed: int = 42) -> None:
    """
    Define a semente aleatória para reprodutibilidade.

    Args:
        seed: Semente aleatória
    """

    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)

    print(f"Semente aleatória definida: {seed}")


def save_model(modelo, metricas, dados, modelo_dir=None, latest=True):
    """
    Coordena o processo de salvamento do modelo treinado e suas métricas.

    Args:
        modelo: Modelo treinado
        metricas: Dict com métricas do classification_report
        dados: Dict com dados adicionais (X, estatísticas, etc.)
        modelo_dir: Caminho para diretório onde serão salvos os arquivos (opcional)

    Returns:
        str: Caminho do arquivo do modelo salvo ou None se falhar
    """
    # Configuração do diretório
    if modelo_dir is None:
        modelo_dir = Path(__file__).parent.parent / "churn_models"

    modelo_dir = Path(modelo_dir)
    modelo_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        if latest:
            # Salvar o modelo mais recente churn_model_latest.pkl substituindo se existir
            latest_model_file_name = "churn_model_latest.pkl"
            if modelo_dir.exists():
                # Remover o modelo mais recente se existir
                for arquivo in modelo_dir.glob(latest_model_file_name):
                    arquivo.unlink()
            modelo_latest = modelo_dir / latest_model_file_name
            modelo_latest = salvar_arquivo_modelo(modelo, modelo_latest)

        # Find the highest version number
        version_numbers = [
            int(folder.name[1:])
            for folder in modelo_dir.glob("V*")
            if folder.is_dir() and folder.name[1:].isdigit()
        ]
        version = max(version_numbers, default=0) + 1

        # Create new version directory
        version_dir = modelo_dir / f"V{version}"
        version_dir.mkdir(exist_ok=True)

        # Salvar o modelo
        modelo_path = version_dir / f"churn_model_{timestamp}.pkl"
        modelo_path = salvar_arquivo_modelo(modelo, modelo_path)

        # Salvar as métricas
        metricas_path = salvar_arquivo_metricas(
            metricas, dados, modelo, version_dir, timestamp
        )

        print(f"Modelo salvo em: {modelo_path}")
        print(f"Métricas salvas em: {metricas_path}")
        return modelo_path

    except Exception as e:
        print(f"Erro ao salvar modelo ou métricas: {e}")
        return None


def salvar_arquivo_modelo(modelo, path):
    with open(path, "wb") as f:
        pickle.dump(modelo, f)

    return path


def salvar_arquivo_metricas(
    metricas_dict, dados_df, modelo, modelo_dir, timestamp
):
    """Salva as métricas do modelo em um arquivo CSV."""
    metricas_path = modelo_dir / f"metricas_{timestamp}.csv"
    rows = [["modelo", modelo.__class__.__name__]]

    # Adicionar métricas básicas
    for metrica in ["accuracy", "precision", "recall", "f1"]:
        if metrica in metricas_dict:
            rows.append([metrica, metricas_dict[metrica]])

    # Extrair nomes das features se disponíveis
    feature_names = []
    if (
        isinstance(dados_df, dict)
        and "X" in dados_df
        and hasattr(dados_df["X"], "columns")
    ):
        feature_names = dados_df["X"].columns.tolist()

    # Adicionar feature importances
    importances = None
    if "feature_importances" in metricas_dict:
        importances = metricas_dict["feature_importances"]
    elif hasattr(modelo, "feature_importances_"):
        importances = modelo.feature_importances_

    if importances is not None:
        for i, imp in enumerate(importances):
            name = (
                feature_names[i] if i < len(feature_names) else f"feature_{i}"
            )
            rows.append([f"importance_{name}", imp])

    # Adicionar outras métricas simples
    skip_keys = [
        "accuracy",
        "precision",
        "recall",
        "f1",
        "feature_importances",
    ]
    for key, value in metricas_dict.items():
        if key not in skip_keys and not isinstance(
            value, (dict, list, np.ndarray)
        ):
            rows.append([key, value])

    # Adicionar dados adicionais simples
    if isinstance(dados_df, dict):
        for key, value in dados_df.items():
            if key != "X" and not isinstance(
                value, (pd.DataFrame, list, dict, set, np.ndarray)
            ):
                rows.append([key, value])

    # Salvar CSV
    with open(metricas_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["metric", "value"])
        writer.writerows(rows)

    return metricas_path
