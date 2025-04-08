# Sistema de Gestão de Academia com IA

Este projeto implementa um sistema de gestão para academias com funcionalidades de IA para previsão de churn de alunos.

## Documentação da API

- Swagger: http://127.0.0.1:8000/docs
- Redoc: http://127.0.0.1:8000/redoc

## Requisitos

- Python 3.10+
- PostgreSQL
- RabbitMQ
- Dependências listadas em `requirements.txt`

## Configuração do Ambiente

### Instalação com Conda

```bash
# Criar ambiente conda
conda create -n pacto_challenge python=3.13
conda activate pacto_challenge

# Instalar dependências
pip install -r requirements.txt
```

### Configuração com Docker

```bash
# Construir e iniciar os containers
docker-compose up -d
```

## Variáveis de Ambiente

Copie o arquivo `.env.example` para `.env` e configure as variáveis necessárias:

```bash
cp .env.example .env
# Edite o arquivo .env conforme necessário
```

## Banco de Dados

Para configurar o banco de dados:

```bash
# Opção 1: Usando o script de setup
python -m challenge.models.setup

# Opção 2: Se estiver usando Docker
docker-compose up postgres -d
```

## Executando o Projeto

### Executando Localmente

```bash
# Iniciar a API
task run

# Executar testes
task test

# Verificação de linting
task lint

# Formatar código
task format
```

### Executando os Workers RabbitMQ

```bash
# Consumidor de checkins em lote
python -m challenge.rabbitmq.consumers.batch_checkin_consumer

# Consumidor de relatórios
python -m challenge.rabbitmq.consumers.relatorio_consumer

# Consumidor de modelo de churn
python -m challenge.rabbitmq.consumers.modelo_churn_consumer
```

## Machine Learning

Para treinar o modelo de churn:

```bash
# Treinamento do modelo via notebook
jupyter notebook challenge/machine_learning/pipeline.ipynb

# Treinamento do modelo via script
python -m challenge.machine_learning.pipeline
```

## Estrutura do Projeto

```
challenge/
├── api/             # Endpoints da API
├── data/            # Utilitários de dados
├── machine_learning/# Modelos de IA e pipeline
├── models/          # Entidades e schemas
├── rabbitmq/        # Infraestrutura de mensageria
├── relatorios/      # Relatórios gerados
├── tests/           # Testes automatizados
└── app.py           # Ponto de entrada da aplicação
```

## Autores

- Hugo Moreno
