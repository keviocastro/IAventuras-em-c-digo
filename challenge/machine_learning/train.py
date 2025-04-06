import pickle
from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# Adicionar diretório raiz ao path
sys.path.append(str(Path(__file__).parent.parent))
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
        modelo_path = salvar_modelo(modelo, report, stats)

        # Adicionar feature importance ao resultado
        stats["feature_importance"] = dict(
            zip(X.columns, modelo.feature_importances_)
        )
        stats["modelo_path"] = modelo_path

        return stats

    except Exception as e:
        print(f"Erro no treinamento: {e}")
        return None


def salvar_modelo(modelo, metricas, dados):
    """
    Salva o modelo treinado e suas métricas

    Args:
        modelo: Modelo treinado
        metricas: Dict com métricas do classification_report
        dados: Dict com dados adicionais (X, estatísticas, etc.)

    Returns:
        str: Caminho do arquivo do modelo salvo ou None se falhar
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    modelos_dir = Path(__file__).parent.parent / "modelos"
    modelos_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Salvar o modelo
        modelo_path = modelos_dir / f"churn_model_{timestamp}.pkl"
        modelo_latest = modelos_dir / "churn_model_latest.pkl"

        with open(modelo_path, "wb") as f:
            pickle.dump(modelo, f)

        with open(modelo_latest, "wb") as f:
            pickle.dump(modelo, f)

        # Salvar as métricas
        metricas_path = modelos_dir / f"metricas_{timestamp}.txt"
        with open(metricas_path, "w") as f:
            # Informações gerais
            f.write(f"Data de treinamento: {datetime.now().isoformat()}\n")
            f.write(f"Total de alunos: {dados.get('total_alunos', 'N/A')}\n")
            f.write(
                f"Total de registros: {dados.get('total_registros', 'N/A')}\n"
            )
            f.write(f"Acurácia: {dados.get('acuracia', 'N/A')}\n\n")

            # Métricas de classificação
            for classe in ["0", "1"]:
                if classe in metricas:
                    f.write(f"Classe {classe}:\n")
                    f.write(
                        f"  Precisão: {metricas[classe]['precision']:.4f}\n"
                    )
                    f.write(f"  Recall: {metricas[classe]['recall']:.4f}\n")

            # Feature importance
            X = dados.get("X")
            if X is not None and hasattr(modelo, "feature_importances_"):
                f.write("\nImportância das features:\n")
                for feature, importance in sorted(
                    zip(X.columns, modelo.feature_importances_),
                    key=lambda x: x[1],
                    reverse=True,
                ):
                    f.write(f"  {feature}: {importance:.4f}\n")

        print(f"Modelo salvo em: {modelo_path}")
        print(f"Métricas salvas em: {metricas_path}")
        return modelo_path

    except Exception as e:
        print(f"Erro ao salvar modelo ou métricas: {e}")
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
