import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt 
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
import joblib  
import openpyxl

df = pd.read_excel('treinamento.xlsx')

X = df.drop(columns=['cancelado'])
y = df['cancelado']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

model = LogisticRegression()
model.fit(X_train, y_train)

joblib.dump(model, 'modelo_treinado.pkl')

