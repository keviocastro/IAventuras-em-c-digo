import pickle
from datetime import datetime
from pathlib import Path
import sys

# Adicionar diretório raiz ao path
sys.path.append(str(Path(__file__).parent.parent))

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

from data.utils import save_model
from data.preprocess import preprocess_data


def treinar_modelo_churn():
    """
    Treina um modelo de previsão de churn com base nos dados históricos

    Returns:
        dict: Informações do modelo treinado ou None se houver falha
    """
    # Obter e preparar os dados
    try:
        df = preprocess_data()

        # Preparar features e target
        X = df[
            [
                "dias_desde_cadastro",
                "dias_desde_ultimo_checkin",
                "total_checkins",
                "media_intervalo_checkins",
            ]
        ]
        y = df["status_aluno"]

        # Estatísticas para log
        stats = {
            "total_alunos": len(df["aluno_id"].unique()),
            "total_registros": len(df),
            "X": X,  # Para feature importance
        }

        # Dividir dados em treino e teste
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Treinar o modelo
        modelo = RandomForestClassifier(n_estimators=100, random_state=42)
        modelo.fit(X_train, y_train)

        # Avaliar o modelo
        y_pred = modelo.predict(X_test)
        stats["acuracia"] = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)

        # Salvar modelo e métricas
        modelo_path = save_model(modelo, report, stats)

        # Adicionar feature importance ao resultado
        stats["feature_importance"] = dict(
            zip(X.columns, modelo.feature_importances_)
        )
        stats["modelo_path"] = modelo_path

        return stats

    except Exception as e:
        print(f"Erro no treinamento: {e}")
        return None


if __name__ == "__main__":
    resultado = treinar_modelo_churn()

    if resultado:
        print("\n=== Resultados do Treinamento ===")
        print(f"Acurácia: {resultado['acuracia']:.4f}")
        print(f"Total de alunos: {resultado['total_alunos']}")
        print(f"Total de registros: {resultado['total_registros']}")

        print("\nImportância das features:")
        for feature, importance in sorted(
            resultado["feature_importance"].items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            print(f"  {feature}: {importance:.4f}")
    else:
        print("Falha ao treinar o modelo")
