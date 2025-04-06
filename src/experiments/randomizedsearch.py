from src.steps.optimize import Optimize
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

import logging
from colorama import Fore, init

init(autoreset=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

PATH_FILE = "data/num.csv"

try:
    df = pd.read_csv(PATH_FILE)
    logging.info(Fore.BLUE + f"File loaded: {PATH_FILE}.")
except FileNotFoundError as file_error:
    logging.error(Fore.RED + f"Error: {file_error}")
try:
    X = df.drop(columns=['churn'])
    y = df['churn']
    logging.info(Fore.BLUE + "Features and Target splitted.")
except Exception as cols_error:
    logging.error(Fore.RED + f"Error: {cols_error}")
try:
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )
    logging.info(Fore.BLUE + f"Data successfully splitted -> Train: {X_train.shape} || Test: {X_test.shape}")
except Exception as split_error:
    logging.error(Fore.RED + f"Error: {split_error}")

print("---\n")
print(Fore.YELLOW + "Iniciando otimização de hiperparâmetros com RandomForestClassifier...")

rf_grid = {
    "n_estimators": [50, 100, 200, 300, 500],
    "max_depth": [None, 10, 20, 30, 40, 50],
    "min_samples_split": [2, 5, 10],
    "min_samples_leaf": [1, 2, 4],
    "bootstrap": [True, False],
    "class_weight": ["balanced", "balanced_subsample"],
    "random_state": [10, 42]
}

optimize_rf = Optimize(
    RandomForestClassifier(),
    rf_grid,
    X_train,
    X_test,
    y_train,
    y_test,
    scoring="roc_auc"
)

rf = optimize_rf.with_random_search()

print(Fore.GREEN + "1/2 - Otimização: RandomizedSearchCV com RandomForestClassifier")
print("---\n")
print(Fore.YELLOW + "Iniciando otimização de hiperparâmetros com XGBClassifier...")

xgb_grid = {
    "n_estimators": [100, 300, 500, 700],
    "max_depth": [3, 5, 7, 10],
    "learning_rate": [0.01, 0.05, 0.1, 0.2],
    "subsample": [0.6, 0.8, 1.0],
    "colsample_bytree": [0.6, 0.8, 1.0],
    "gamma": [0, 0.1, 0.3, 0.5],
    "scale_pos_weight": [1, 2, 5]  # Para lidar com o desbalanceamento
}

optimize_xgb = Optimize(
    XGBClassifier(),
    xgb_grid,
    X_train,
    X_test,
    y_train,
    y_test,
    scoring="roc_auc"
)

xgb = optimize_xgb.with_random_search()
print(Fore.GREEN + "2/2 - Otimização: RandomizedSearchCV com XGBClassifier...")
print("Fim da Otimização")
