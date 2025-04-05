## Sistema de Monitoramento de Academia (Gym)

Sistema para monitoramento de frequência de alunos em academia e previsão de desistências (churn) usando FastAPI, PostgreSQL, RabbitMQ e Redis.

### Arquitetura do Sistema

O sistema é estruturado com uma arquitetura distribuída composta por:

- **API REST (FastAPI)**: Backend principal que gerencia todas as operações CRUD e expõe endpoints RESTful.
- **Banco de Dados (PostgreSQL)**: Armazena dados de alunos, checkins, planos e previsões.
- **Sistema de Filas (RabbitMQ)**: Gerencia processamento assíncrono para operações demoradas.
- **Cache (Redis)**: Melhora a performance de operações frequentes.
- **Modelo de IA**: Realiza previsões de churn baseado em dados históricos.
- **Interface Web (Django)**: Frontend simples para visualização dos dados e interação.

### Estrutura de Diretórios

O projeto está organizado da seguinte forma:

# Diretório Raiz
- `README.md`: Documentação principal do projeto
- `requirements.txt`: Dependências globais do projeto
- `.env` e `.env.example`: Configurações de ambiente

# /backend
Contém todo o código relacionado à API REST e processamento de dados:
- `/app`: Código principal da aplicação FastAPI
  - `/api`: Implementação dos endpoints da API
  - `/core`: Configurações essenciais e utilitários
  - `/db`: Operações e configurações do banco de dados
  - `/models`: Definições ORM dos modelos de dados
  - `/queue`: Gerenciamento de filas com RabbitMQ
  - `/schemas`: Esquemas Pydantic para validação de dados
  - `/services`: Serviços de negócios e lógica da aplicação
  - `/static`: Arquivos estáticos da API
  - `main.py`: Ponto de entrada da aplicação FastAPI
- `/models`: Modelo de chrun gerados pelo sistema
- `/reports`: Relatórios gerados pelo sistema
- `init_db.py`: Script para inicialização do banco de dados
- `start_worker.py`: Script para iniciar os workers de processamento
- `README_RABBITMQ.md`: Documentação específica para configuração do RabbitMQ

# /frontend
Contém todo o código da interface web em Django:
- `/dashboard`: Aplicação Django para dashboard administrativo
- `/gym_frontend`: Configurações do projeto Django
- `/static`: Arquivos estáticos (CSS, JS, imagens)
- `/templates`: Templates HTML da interface
- `manage.py`: Script de gerenciamento do Django

# /models
Armazena os modelos treinados no notebook :
- `modelo_churn.pkl`: Modelo de previsão de churn
- `feature_info.pkl`: Informações sobre as features do modelo

# /notebooks
Contém notebooks Jupyter para análise de dados e desenvolvimento de modelos:
- `modelo_churn.ipynb`: Desenvolvimento do modelo de previsão de churn

# /scripts
Scripts utilitários para configuração e teste:
- `create_admin.py`: Criação de usuário administrativo
- `popula_db.py`: População do banco com dados de teste
- `test_redis_cache.py`: Testes do cache Redis



### Componentes do Sistema

### 1. API REST (FastAPI)

Endpoints principais:
- **POST /aluno/registro**: Registra um novo aluno
- **POST /aluno/checkin**: Registra entrada do aluno na academia
- **GET /aluno/{id}/frequencia**: Obtém histórico de frequência
- **GET /aluno/{id}/risco-churn**: Obtém probabilidade de desistência
- **GET /status**: Status do sistema e serviços dependentes
- **Autenticação JWT**: Proteção de endpoints por níveis de acesso

### 2. Banco de Dados (PostgreSQL)

Tabelas principais:
- **alunos**: Informações básicas dos alunos
- **checkins**: Registro de entradas na academia
- **planos**: Tipos de planos disponíveis
- **usuarios**: Usuários administrativos do sistema

### 3. Processamento Assíncrono (RabbitMQ)

Filas implementadas:
- **checkin_queue**: Processamento de checkins em massa
- **daily_report_queue**: Geração de relatórios diários
- **model_update_queue**: Atualização do modelo de previsão
- **churn_probabilities_queue**: Cálculo de probabilidades de churn

### 4. Cache com Redis

Estratégias de cache:
- Cache de frequência de alunos (12 horas de expiração)
- Cache de probabilidades de churn (24 horas de expiração)
- Invalidação automática após atualizações relevantes

### 5. Modelo de IA para Previsão de Churn

Fatores analisados pelo modelo:
- Frequência semanal
- Tempo desde o último checkin
- Duração média das visitas
- Tipo de plano

Implementado como modelo de classificação usando scikit-learn.

## Pré-requisitos

- Python 3.10+
- PostgreSQL
- RabbitMQ
- Redis (opcional, para cache)

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/Gym.git
cd Gym
```

2. Crie um ambiente conda:
```bash
conda create -n gym python=3.10
conda activate gym
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure o banco de dados PostgreSQL:
```bash
# Execute o script de inicialização
python scripts/init_db.py
```

5. Configure as variáveis de ambiente:
```bash
# Crie um arquivo .env baseado no exemplo
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

## Executando a Aplicação

### API (FastAPI)
```bash
cd backend
uvicorn app.main:app --reload
```

### Frontend (Django)
```bash
cd frontend
python manage.py runserver 8001
```

### Processamento Assíncrono (RabbitMQ Worker)
```bash
cd backend
python start_worker.py
```



## Cache com Redis

O sistema utiliza Redis como cache para melhorar a performance de operações frequentes:

- Cache de frequência de alunos (12 horas de expiração)
- Cache de probabilidades de churn (24 horas de expiração)
- Invalidação automática de cache após novos checkins ou atualizações de alunos

Para instalar e executar o Redis:

```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis

# Windows
# Baixe o Redis para Windows em https://github.com/microsoftarchive/redis/releases
```

Verifique o status do Redis no endpoint:
```
GET /status/cache
```

## Endpoints da API

### Alunos
- `POST /aluno/registro`: Registrar um novo aluno
- `GET /aluno/{id}`: Obter detalhes de um aluno
- `PUT /aluno/{id}`: Atualizar informações do aluno
- `PATCH /aluno/{id}/ativar`: Ativar cadastro do aluno
- `PATCH /aluno/{id}/desativar`: Desativar cadastro do aluno

### Checkins
- `POST /aluno/checkin`: Registrar entrada/saída do aluno
- `GET /aluno/{id}/frequencia`: Obter histórico de frequência

### Previsão de Churn
- `GET /aluno/{id}/risco-churn`: Obter probabilidade de desistência
- `POST /admin/atualizar-modelo`: Atualizar modelo de previsão

### Autenticação
- `POST /auth/token`: Obter token JWT
- `GET /auth/usuarios`: Listar usuários (admin)
- `POST /auth/usuarios`: Criar usuário (admin)

## Modelo de Previsão de Churn

O modelo de IA analisa os seguintes fatores para prever desistências:
- Frequência semanal
- Tempo desde o último checkin
- Duração média das visitas
- Tipo de plano

O algoritmo utilizado é um  de classificação com Random Forest, implementado em scikit-learn. 

Para verificar o treinamento e entender o modelo, consulte:
```
notebooks/modelo_churn.ipynb
```



### Como testar

- crie um abiente e instale as dependencias, garanta que o postgresql esta instalado e rodando, instale o redis cache
- execute o "init_db.py" da pasta backend para inicializar o banco
- execute o "popula_db.py" da pasta de scripts para criar dados artificiais de alunos e popular o banco
- execute o "create_admin.py" da pasta de scripts para criar usuario admin
- rode "uvicorn app.main:app --reload" na pasta backend para iniciar a API
- rode "python manage.py runserver 8001" na pasta frontend para iniciar o django e a interface grafico
- rode "python start_worker.py" na pasta backend para iniciar a fila
- acesse no navegador "localhost:8001" para acessar a interface desenvolvida para teste
- faça login com usuario e senha "admin" , caso o sistema parece de receber informações e receba erros de credencial, faça logout e login novamente, a detecção de expiração do token não foi implementada ainda
- Funções maiores usam a fila (treinamento de modelo, checkin em massa,geração de relatorio, atualização de churn para todos...)
- Funções leves sao feitas de forma sincrona (criação de usuario unico, checkin ...)
- A função de criar aluno sintetico foi feita para ver melhor o funcionamento do modelo, treine o mesmo primeiro com a base populada e posteriormente crie alunos sinteticos com diferentes perfis para teste

## Documentação da API

A documentação da API estará disponível em:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Recursos Adicionais

- ✅ Autenticação JWT
- ✅ Cache com Redis