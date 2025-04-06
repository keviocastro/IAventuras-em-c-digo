
# Gym API

API construída com FastAPI para gerenciar uma academia.

---

## Descrição

Esta API foi desenvolvida com o objetivo de gerenciar uma academia e expor um modelo de Machine Learning via HTTP, utilizando o framework FastAPI. A API registra, faz check-in, check-out, emite relatório de frequência, e retorna também a probabilidade de um aluno cancelar seu plano. O modelo realiza previsões com base nos dados recebidos no corpo da requisição. A API é auto-documentada e pronta para deploy em ambientes de produção ou testes.

---

## Tecnologias Utilizadas

- Python 3.11+
- FastAPI
- Uvicorn
- Pydantic
- Typer (para CLI de geração de docs)
- JSON (OpenAPI Spec)
- HTML (Documentação offline com Redoc)
- Pickle
- RabbitMQ

---

## Como Rodar a API

```bash
PYTHONPATH=. python3 main.py
```

A API estará acessível em: [http://localhost:8000](http://localhost:8000)

---

## Documentação da API

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Endpoints
### `POST` /aluno/registro

Registra um novo aluno com seus dados, plano e matrícula.

### `POST` /aluno/checkin

Registra um check-in do aluno na academia.

### `POST` /aluno/checkout

Registra um check-out do aluno na academia.

### `POST` /aluno/{id}/frequencia

Este endpoint gera um relatório com o histórico de frequência de um aluno.

### `POST` /aluno/{id}/risco-churn

ste endpoint retorna a probabilidade de um aluno cancelar sua inscrição.
