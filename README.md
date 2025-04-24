# Teste Prático para Engenheiro de IA - Nível Júnior

## Contexto
Uma academia de ginástica precisa de um sistema para monitorar a frequência dos alunos e prever possíveis desistências (churn). O sistema deve processar dados de entrada dos alunos na academia e gerar insights para a equipe de retenção.

## Requisitos Técnicos

### Parte 1: API e Banco de Dados
1. Criar uma API REST usando Flask ou FastAPI com os seguintes endpoints:
   - `POST /aluno/registro`: Registrar um novo aluno
   - `POST /aluno/checkin`: Registrar entrada do aluno na academia
   - `GET /aluno/{id}/frequencia`: Obter histórico de frequência
   - `GET /aluno/{id}/risco-churn`: Obter probabilidade de desistência

2. Implementar um banco de dados PostgreSQL com as seguintes tabelas:
   - `alunos`: Informações básicas dos alunos
   - `checkins`: Registro de entradas na academia
   - `planos`: Tipos de planos disponíveis

### Parte 2: Processamento Assíncrono
1. Implementar um sistema de filas usando RabbitMQ para:
   - Processar checkins em massa
   - Gerar relatórios diários de frequência
   - Atualizar o modelo de previsão de churn

### Parte 3: Modelo de IA para Previsão de Churn
1. Desenvolver um modelo simples de machine learning para prever a probabilidade de um aluno cancelar a matrícula baseado em:
   - Frequência semanal
   - Tempo desde o último checkin
   - Duração média das visitas
   - Tipo de plano

## Entregáveis
1. Código fonte completo no GitHub
2. Documentação da API (Swagger ou similar)
3. Script para inicialização do banco de dados
4. Arquivo README com instruções de instalação e execução
5. Notebook Jupyter demonstrando o treinamento do modelo de previsão de churn

## Critérios de Avaliação
- Qualidade e organização do código
- Funcionalidade da API
- Implementação correta do sistema de filas
- Performance e precisão do modelo de previsão
- Documentação e facilidade de setup

## Bônus (opcional)
- Implementar cache com Redis para melhorar performance
- Adicionar autenticação JWT na API
- Containerizar a aplicação com Docker
- Implementar testes unitários

## Instruções de Entrega
1. Faça um fork deste repositório
2. Desenvolva a solução em seu fork
3. Crie um Pull Request para este repositório com sua solução
4. Envie um email para rh@pactosolucoes.com.br contendo:
   - Seu currículo
   - Link do Pull Request criado
   - Informações de contato


# Pulse Fit

**Pulse Fit** é um sistema desenvolvido em Flask para gerenciar academias, incluindo funcionalidades como check-ins de alunos, geração de relatórios, envio de e-mails e monitoramento de alunos em risco.

---

## 📋 Funcionalidades

- **Check-in de Alunos**: Registro de entrada e saída dos alunos.
- **Relatórios**: Geração de relatórios em formato `.txt` e envio por e-mail.
- **Fila de Processamento**: Uso do RabbitMQ para processamento assíncrono de tarefas.
- **Monitoramento de Alunos em Risco**: Identificação de alunos com baixa frequência.
- **Integração com Banco de Dados**: Suporte a PostgreSQL.
- **Envio de E-mails**: Configuração para envio de relatórios via Gmail ou outros provedores SMTP.

---

## 🛠️ Tecnologias Utilizadas

- **Backend**: Flask
- **Banco de Dados**: PostgreSQL
- **Mensageria**: RabbitMQ
- **Frontend**: HTML, CSS (Bootstrap)
- **Outros**:
  - Flask-Mail
  - Flask-Migrate
  - SQLAlchemy
  - APScheduler

---

## 🚀 Como Executar o Projeto

### ⚙️ Pré-requisitos

- Python 3.9 ou superior
- PostgreSQL
- RabbitMQ
- Ambiente virtual configurado (`venv`)

### 📦 Passos para rodar localmente

1. **Clone o repositório**:
   ```bash
   git clone https://github.com/seu-usuario/pulse-fit.git
   cd pulse-fit
   ```

2. **Crie e ative o ambiente virtual**:
   ```bash
   python -m venv venv
   source venv/bin/activate        # Linux/MacOS
   venv\Scripts\activate           # Windows
   ```

3. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Crie o banco de dados no PostgreSQL**:

   No seu PostgreSQL, crie o banco chamado `pulsefit`:
   ```sql
   CREATE DATABASE pulsefit;
   ```

5. **Configure as credenciais do banco em `academia/__init__.py`**:
   ```python
   app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://usuario:senha@localhost:5432/pulsefit"
   ```

6. **Gere as migrações e aplique-as**:
   ```bash
   flask db init        # (se ainda não foi iniciado)
   flask db migrate -m "Criação das tabelas"
   flask db upgrade
   ```

7. **Popule o banco de dados com dados iniciais**:
   ```bash
   python gerar_dados_para_db.py
   ```

8. **Inicie o RabbitMQ**:
   Certifique-se de que o RabbitMQ está em execução:
   ```bash
   rabbitmq-server
   ```

9. **Execute a aplicação**:
   ```bash
   python run.py
   ```

10. **Acesse no navegador**:
    ```
    http://127.0.0.1:5000
    ```
    caso queira ver o projeto rodando... so entrar no link: [pulse-fit](https://pulse-fit.onrender.com/)

---

## 📧 Configuração de E-mail

Para envio de relatórios por e-mail, configure as credenciais SMTP no `academia/__init__.py`:

```python
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'seu_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'sua_senha_de_aplicativo'
app.config['MAIL_DEFAULT_SENDER'] = 'seu_email@gmail.com'
```

---

## 📂 Estrutura do Projeto

```
Pulse_Fit/
├── academia/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   ├── templates/
│   │   ├── aluno_risco.html
│   │   └── ...
│   ├── relatorio/
│   │   ├── utils.py
│   │   ├── worker_relatorio.py
│   │   ├── agendador.py
│   │   └── relatorio_alunos.py
├── gerar_dados_para_db.py
├── run.py
├── requirements.txt
└── README.md
```

---

## 📜 Licença

Este projeto está sob a licença MIT. Sinta-se à vontade para usá-lo e modificá-lo.
