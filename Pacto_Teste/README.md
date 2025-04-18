# Sistema de Gestão de Academia com IA

Implementação de sistema de gestão para academias com funcionalidades de IA para previsão de churn de alunos.

## Documentação da API

- Swagger: http://127.0.0.1:8000/docs

## Requisitos

- **Python** 3.10+
- **PostgreSQL** 13+
- **RabbitMQ** 3.x
- **Docker** e **Docker Compose** (opcional, para execução via containers)
- Dependências listadas no arquivo `requirements.txt`

## Configuração do Ambiente

### Instalação Local

### Clone o repositório:

```bash
git clone https://github.com/Pedro-Reis2/IAventuras-em-c-digo.git

# Instalar dependências
pip install -r requirements.txt
```

### Configuração com Docker

```bash
# Construa e inicie os containers:
docker-compose up --build
```

## Executando o Projeto

Localmente:

1- Inicie a API:

```bash
uvicorn app.main:app --reload
```
2- Execute os consumidores RabbitMQ:

```bash
python -m app.consumers.consumer
python -m app.consumers.churn_consumer
python -m app.consumers.schedule_consumer
```
3- Execute o agendador:

```bash
python -m app.utils.scheduler
```
Com Docker:

```bash
docker-compose up
```

## Estrutura do Projeto

```
app/
├── consumers/             # Consumidores RabbitMQ
├── utils/                 # Utilitários e scripts auxiliares
├── [churn_model.py]       # Funções relacionadas ao modelo de churn
├── [database.py]          # Configuração do banco de dados
├── [main.py]              # Ponto de entrada da API
├── [models.py]            # Definições de tabelas e entidades
├── churn_model.pkl        # Modelo treinado de churn
data/
├── df_alunos_novo.csv     # Dados de alunos
├── df_checkins2.csv       # Dados de check-ins
notebooks/
├── [churn_training.ipynb] # Notebook para treinamento do modelo
[Dockerfile.api]           # Dockerfile para a API
[Dockerfile.consumer]      # Dockerfile para consumidores
[docker-compose.yml]       # Configuração do Docker Compose
```

- Pedro Reis
