
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

> ⚡ **Este projeto deve ser executado via Docker.**

### ⚙️ Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/)

### 📦 Passos para rodar com Docker


1. **Execute o projeto usando Docker Compose**:
   ```bash
   docker-compose up -d --build
   ```

   - O comando acima irá:
     - Construir as imagens necessárias.
     - Subir o banco de dados PostgreSQL e a aplicação Flask.
     - Popular automaticamente o banco de dados com dados iniciais.

2. **Acesse a aplicação no navegador**:
   ```
   http://localhost:5000
   ```

---

## 📧 Configuração de E-mail

Para envio de relatórios por e-mail, configure as credenciais SMTP no arquivo `academia/__init__.py`:

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
├── docker-compose.yml
├── Dockerfile
└── README.md
```

---

## 📜 Licença

Este projeto está sob a licença MIT. Sinta-se à vontade para usá-lo e modificá-lo.
