# Implementação de RabbitMQ no Sistema de Academia

Este documento descreve a implementação do sistema de mensageria assíncrona usando RabbitMQ no sistema de monitoramento da academia.

## Visão Geral

O RabbitMQ foi implementado para processar as seguintes operações de forma assíncrona:

1. **Processamento de check-ins em massa**: Permite registrar grandes volumes de check-ins sem bloquear a API.
2. **Geração de relatórios diários**: Gera relatórios diários de frequência de forma assíncrona.
3. **Atualização do modelo de predição de churn**: Treina e atualiza o modelo de predição de desistência de alunos.

## Pré-requisitos

Para usar o sistema com RabbitMQ, você precisa ter:

- RabbitMQ Server instalado e em execução
- Python 3.8+
- Dependências do projeto instaladas (`pip install -r requirements.txt`)

## Configuração do RabbitMQ

A configuração do RabbitMQ é feita através de variáveis de ambiente:

```
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
```

Estas configurações podem ser ajustadas no arquivo `.env` na raiz do projeto ou definidas diretamente no ambiente.

## Iniciando o Worker

Para processar as mensagens nas filas RabbitMQ, é necessário iniciar o worker usando o seguinte comando:

```bash
# No diretório backend
python start_worker.py
```

O worker iniciará threads separadas para cada tipo de fila e processará as mensagens conforme chegarem.

## Endpoints da API

Os seguintes endpoints foram adicionados para usar as funcionalidades do RabbitMQ:

### Processamento de Check-ins em Massa

- `POST /checkin/batch`: Registra múltiplos check-ins de forma assíncrona.

Exemplo de requisição:
```json
[
  {"aluno_id": 1},
  {"aluno_id": 2},
  {"aluno_id": 3}
]
```

### Geração de Relatórios

- `POST /relatorio/diario`: Solicita a geração de um relatório diário de frequência.

Parâmetros opcionais:
- `data`: Data no formato ISO (YYYY-MM-DD). Se não for fornecida, será usada a data atual.

### Atualização do Modelo de Predição

- `POST /relatorio/churn/atualizar-modelo`: Solicita a atualização do modelo de predição de churn.

### Status do Sistema

- `GET /status`: Verifica o status do sistema, incluindo a conexão com o RabbitMQ.

## Arquitetura

A implementação do RabbitMQ segue a seguinte arquitetura:

1. **Client (RabbitMQClient)**: Classe que encapsula a conexão e interação com o RabbitMQ.
2. **Producers**: Funções que enviam mensagens para as filas.
3. **Consumers**: Funções que processam as mensagens das filas.
4. **Worker**: Script que inicia os consumidores em threads separadas para processar as mensagens.

## Filas

Foram definidas as seguintes filas:

1. **CHECKIN_QUEUE**: Para processamento de check-ins em massa.
2. **REPORT_QUEUE**: Para geração de relatórios diários.
3. **MODEL_UPDATE_QUEUE**: Para atualização do modelo de predição de churn.

## Logs

Os logs do worker e da API são configurados para mostrar informações sobre o processamento das mensagens e quaisquer erros encontrados.

## Manutenção

Para verificar o status das filas e mensagens, você pode usar a interface web do RabbitMQ, geralmente disponível em http://localhost:15672 (credenciais padrão: guest/guest).

## Troubleshooting

Se ocorrer erro na conexão com o RabbitMQ:

1. Verifique se o servidor RabbitMQ está em execução
2. Confirme que as credenciais estão corretas
3. Verifique se as portas necessárias estão abertas
4. Consulte os logs para mensagens de erro específicas