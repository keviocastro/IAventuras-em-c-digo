import pandas as pd
from typing import Tuple, List, Dict, Union, Optional, Any

from sklearn.model_selection import (
    cross_val_score,
)
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)
from sklearn.base import BaseEstimator


def evaluate_model(
    model: BaseEstimator,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    threshold: float = 0.5,
) -> Dict[str, float]:
    """
    Avalia o modelo com métricas comuns de classificação.

    Args:
        model: Modelo treinado
        X_test: Features de teste
        y_test: Target de teste
        threshold: Limiar para classificação binária (para probs)

    Returns:
        Dicionário com métricas de avaliação
    """
    # Verificar se o modelo tem método predict_proba

    # Fazer predições
    y_pred = model.predict(X_test)

    # Calcular métricas
    try:
        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred),
            "recall": recall_score(y_test, y_pred),
            "f1": f1_score(y_test, y_pred),
        }
    except ValueError as e:
        print(f"Erro ao calcular métricas: {e}")

    # Feature importance se o modelo suportar
    if hasattr(model, "feature_importances_"):
        feature_importances = model.feature_importances_
        metrics["feature_importances"] = feature_importances

    # if hasattr(model, "predict_proba"):
    #     y_probas = model.predict_proba(X_test)
    #     # Check if we have a 2D array with more than one column
    #     if y_probas.shape[1] > 1:
    #         y_proba = y_probas[:, 1]
    #     else:
    #         y_proba = y_probas[:, 0]
    #     # Aplicar threshold personalizado se necessário
    #     if threshold != 0.5:
    #         y_pred = (y_proba >= threshold).astype(int)

    #     metrics["roc_auc"] = roc_auc_score(y_test, y_proba)

    return metrics


def print_model_evaluation(model_name: str, metrics: Dict[str, float]) -> None:
    print(f"=== Avaliação do modelo: {model_name} ===")
    print(f"Acurácia: {metrics['accuracy']:.4f}")
    print(f"Precisão: {metrics['precision']:.4f}")
    print(f"Recall: {metrics['recall']:.4f}")
    print(f"F1-Score: {metrics['f1']:.4f}")

    if "roc_auc" in metrics:
        print(f"ROC AUC: {metrics['roc_auc']:.4f}")

    print("=" * 50)


def cross_validate_model(
    model: BaseEstimator,
    X: pd.DataFrame,
    y: pd.Series,
    cv: int = 5,
    metrics: List[str] = ["accuracy"],
) -> Dict[str, List[float]]:
    """
    Realiza validação cruzada do modelo.

    Args:
        model: Modelo a ser validado
        X: Features
        y: Target
        cv: Número de folds
        metrics: Lista de métricas para avaliação

    Returns:
        Dicionário com resultados para cada métrica
    """
    results = {}

    for metric in metrics:
        scores = cross_val_score(model, X, y, cv=cv, scoring=metric)
        results[metric] = scores
        print(f"{metric}: {scores.mean():.4f} (+/- {scores.std():.4f})")

    return results
