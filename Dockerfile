FROM python:3.13.2

WORKDIR /pulse_fit

COPY . .

RUN pip install -r requirements.txt

# Inicializa o banco, cria as migrações e aplica
RUN flask --app run.py db init || true
RUN flask --app run.py db migrate -m "criação das tabelas iniciais" || true
RUN flask --app run.py db upgrade || true

# Instala o netcat, necessário para verificar se o banco está pronto
RUN apt-get update && apt-get install -y netcat-openbsd

# Permissão para entrypoint
RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]
