import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    recall_score,
    precision_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report
)
import pickle
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
logging.info(Fore.YELLOW + "Iniciando otimização de hiperparâmetros com RandomForestClassifier...")

try:
    model = RandomForestClassifier(
        bootstrap=True,
        class_weight="balanced",
        max_depth=30,
        min_samples_leaf=2,
        min_samples_split=5,
        n_estimators=100,
        random_state=42
    )
    model.fit(X_train, y_train)
    logging.info(Fore.GREEN + "Model training is complete.")
except Exception as fit_error:
    logging.error(Fore.RED + f"Error: {fit_error}")

try:
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    rocauc = roc_auc_score(y_test, y_proba)
    cm = confusion_matrix(y_test, y_pred)
    cr = classification_report(y_test, y_pred)
    logging.info(Fore.GREEN + "Predictions is done. Check this metrics:\n")
except Exception as pred_and_eval_error:
    logging.error(Fore.RED + f"Error: {pred_and_eval_error}")

print("1. Classification Report\n", cr)
print("\n2. Confusion Matrix\n", cm)
print("\n3. ROC AUC Score: ", rocauc)
print("\n4. Accuracy Score: ", acc)
print("\n5. Precision Score: ", precision)
print("\n6. Recall Score: ", recall)
print("\n7. F1 Score: ", f1)

try:
    MODEL_PATH = "src/models/model.pkl"
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    logging.info(Fore.GREEN + f"Model saved on: {MODEL_PATH}")
except FileNotFoundError as dir_not_found_error:
    logging.error(Fore.RED + f"Error: {dir_not_found_error}")
