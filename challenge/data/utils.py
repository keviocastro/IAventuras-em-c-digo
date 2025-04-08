import pandas as pd
from typing import Tuple, List, Dict, Union, Optional, Any

from .vars import TARGET_COLS


from sklearn.model_selection import (
    train_test_split,
    KFold,
    StratifiedKFold,
)
from sklearn.preprocessing import StandardScaler, MinMaxScaler


def split_train_val_test(
    data: pd.DataFrame,
    test_size: float = 0.1,
    val_size: float = 0.1,
    random_state: int = 42,
    stratify_col: str = "status_aluno",
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Divide os dados em conjuntos de treino, validação e teste.

    Args:
        data: DataFrame com os dados
        test_size: Proporção dos dados para teste
        val_size: Proporção dos dados para validação (relativa aos dados após separar teste)
        random_state: Semente aleatória
        stratify_col: Coluna para estratificar a divisão

    Returns:
        Tupla com (train_data, val_data, test_data)
    """
    # Verificar se a coluna de estratificação existe
    stratify = data[stratify_col] if stratify_col in data.columns else None

    # Separar dados de teste
    train_val_data, test_data = train_test_split(
        data, test_size=test_size, random_state=random_state, stratify=stratify
    )

    # Atualizar stratify para a nova divisão
    stratify = (
        train_val_data[stratify_col] if stratify_col in data.columns else None
    )

    # Separar dados de treino e validação
    train_data, val_data = train_test_split(
        train_val_data,
        test_size=val_size,
        random_state=random_state,
        stratify=stratify,
    )

    print(f"Tamanho do conjunto de treino: {len(train_data)} registros")
    print(f"Tamanho do conjunto de validação: {len(val_data)} registros")
    print(f"Tamanho do conjunto de teste: {len(test_data)} registros")

    return train_data, val_data, test_data


def split_data_kfold(
    data: pd.DataFrame,
    k: int = 5,
    stratify: bool = True,
    random_state: int = 42,
) -> List[Tuple]:
    """
    Divide os dados em k-folds para validação cruzada.

    Args:
        data: DataFrame com os dados
        k: Número de folds
        stratify: Se True, usa StratifiedKFold para manter a proporção das classes
        random_state: Semente aleatória

    Returns:
        Lista de tuplas (train_data, test_data)
    """
    if stratify and "status_aluno" in data.columns:
        kf = StratifiedKFold(
            n_splits=k, shuffle=True, random_state=random_state
        )
        splits = list(kf.split(data, data["status_aluno"]))
    else:
        kf = KFold(n_splits=k, shuffle=True, random_state=random_state)
        splits = list(kf.split(data))

    folds = []
    for train_index, test_index in splits:
        train_data = data.iloc[train_index]
        test_data = data.iloc[test_index]
        folds.append((train_data, test_data))

    return folds


def get_X_y(
    data: pd.DataFrame,
    target_col: str = TARGET_COLS[0],
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Separa os dados em features (X) e target (y).

    Args:
        data: DataFrame com os dados
        target_col: Nome da coluna target
        exclude_cols: Lista de colunas adicionais a serem excluídas das features

    Returns:
        Tupla (X, y)
    """

    X = data.drop(columns=[target_col])
    y = data[target_col]

    return X, y


def scale_features(
    X_train: pd.DataFrame,
    X_val: Optional[pd.DataFrame] = None,
    X_test: Optional[pd.DataFrame] = None,
    scaler_type: str = "standard",
) -> Tuple:
    """
    Escala as features usando o scaler especificado.

    Args:
        X_train: Features de treino
        X_val: Features de validação
        X_test: Features de teste
        scaler_type: Tipo de scaler ('standard' ou 'minmax')

    Returns:
        Tuple contendo (X_train_scaled, X_val_scaled, X_test_scaled, scaler)
    """
    if scaler_type.lower() == "standard":
        scaler = StandardScaler()
    elif scaler_type.lower() == "minmax":
        scaler = MinMaxScaler()
    else:
        raise ValueError("scaler_type deve ser 'standard' ou 'minmax'")

    X_train_scaled = pd.DataFrame(
        scaler.fit_transform(X_train),
        columns=X_train.columns,
        index=X_train.index,
    )

    result = [X_train_scaled, scaler]

    if X_val is not None:
        X_val_scaled = pd.DataFrame(
            scaler.transform(X_val), columns=X_val.columns, index=X_val.index
        )
        result.insert(1, X_val_scaled)

    if X_test is not None:
        X_test_scaled = pd.DataFrame(
            scaler.transform(X_test),
            columns=X_test.columns,
            index=X_test.index,
        )
        result.insert(-1, X_test_scaled)

    return tuple(result)
