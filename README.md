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
