from pathlib import Path
import sys

# Adicionar diretório raiz ao path
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent))

from sklearn.ensemble import RandomForestClassifier

from data.preprocess import preprocess_data

from data.utils import split_train_val_test, get_X_y
from machine_learning.utils import set_seed, evaluate_model


def treinar_modelo_churn():
    """
    Treina um modelo de previsão de churn com base nos dados históricos

    Returns:
        dict: Informações do modelo treinado ou None se houver falha
    """
    # Obter e preparar os dados
    try:
        set_seed(42)

        df = preprocess_data()

        train_data, val_data, test_data = split_train_val_test(
            df, test_size=0.2, val_size=0.2
        )

        X_train, y_train = get_X_y(train_data)
        X_val, y_val = get_X_y(val_data)
        X_test, y_test = get_X_y(test_data)

        # Treinar o modelo
        modelo = RandomForestClassifier(n_estimators=100, random_state=42)
        modelo.fit(X_train, y_train)

        # Avaliar o modelo
        metrics = evaluate_model(model=modelo, X_test=X_test, y_test=y_test)

        print("Relatório de Classificação:")
        # Display metrics in a readable format
        for key, value in metrics.items():
            if (
                key != "feature_importances"
            ):  # Handle feature importances separately
                print(f"{key.capitalize()}: {value:.4f}")

        # Display feature importances
        print("\nFeature Importances:")
        feature_names = X_train.columns
        importances = metrics["feature_importances"]
        for feature, importance in zip(feature_names, importances):
            print(f"{feature}: {importance:.4f}")

        return modelo, metrics, df

    except Exception as e:
        print(f"Erro no treinamento: {e}")
        return None


if __name__ == "__main__":
    resultado = treinar_modelo_churn()
    if resultado:
        modelo, metrics, df = resultado
        print("Modelo treinado com sucesso.")
    else:
        print("Falha ao treinar o modelo")
