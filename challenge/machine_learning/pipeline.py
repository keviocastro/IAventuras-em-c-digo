from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent))

from machine_learning.train import treinar_modelo_churn
from machine_learning.utils import save_model


def pipeline():
    """
    Função principal da pipeline de treinamento do modelo de churn.
    """
    # Treinar o modelo
    modelo, metricas, dados = treinar_modelo_churn()

    modelo_path = save_model(modelo, metricas, dados)

    if modelo:
        print("Modelo treinado com sucesso.")
        return modelo, metricas, dados, modelo_path
    else:
        print("Falha ao treinar o modelo.")
        return None


if __name__ == "__main__":
    modelo = treinar_modelo_churn()
    if modelo:
        print("Modelo treinado e salvo com sucesso.")
    else:
        print("Falha ao treinar o modelo.")
