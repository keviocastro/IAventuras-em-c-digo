#!/bin/bash
set -e

echo "Aguardando banco de dados..."
while ! nc -z db 5432; do
  sleep 1
done
echo "Banco de dados pronto!"

echo "Aguardando RabbitMQ..."
while ! nc -z rabbitmq 5672; do
  sleep 1
done
echo "RabbitMQ pronto!"

echo "Aplicando migrações..."
flask --app run.py db upgrade

echo "Populando banco de dados (se necessário)..."
python gerar_dados_para_db.py

echo "Iniciando aplicação..."
python run.py
