# Instruções para execução

Para executar esta API é necessário que a máquina possua os seguintes softwares instalados:

- git
- python3, python3-venv, python3-pip
- postgresql, postgresql-contrib, libpq-dev

## 1. Download e configurações

1. Abra o terminal, navegue até a pasta onde o projeto será baixado e execute o comando: git clone git@github.com:pauloprbs/IAventuras-em-c-digo.git
2. Agora entre na pasta do projeto usando: cd IAventuras-em-c-digo
3. Então criaremos o ambiente virtual e instalaremos as dependências. Use os comandos a seguir:
    - Criar ambiente virtual: python3 -m venv venv
    - Ativar ambiente virtual: source venv/bin/activate
    - Instalação das dependências: pip install -r requirements.txt
4. O próximo passo é criar o banco de dados:
    - No terminal, use o comando a seguir para acessar o Postgres: sudo -u postgres psql
    - Então criamos o banco de dados: CREATE DATABASE academia;
    - Também vamos criar um usuário: CREATE USER pacto WITH ENCRYPTED PASSWORD 'pacto123';
    - Por fim, damos acesso ao banco de dados a este usuário: GRANT ALL PRIVILEGES ON DATABASE academia TO meu_usuario;
    - Agora podemos sair do psql: \q
5. Usaremos o Alembic para as migrações, então precisamos fazer a migração inicial com os comandos:
    - alembic revision --autogenerate -m "Initial migration"
    - alembic upgrade head
6. Verifique as tabelas através do psql:
    - psql -h localhost -U pacto academia
    - \dt
    - O comando acima deve mostrar as 3 tabelas criadas.
7. Agora vamos popular o banco de dados. No terminal, use os seguintes scripts:
    - python -m scripts.populate_db_planos
    - python -m scripts.populate_db_alunos
    - python -m scripts.populate_db_checkins
8. Os models usados para criar as tabelas estão setados com autoincrement, e como os scripts adicionam dados "por fora" da api, o autoincrement não fica atualizado. Por isso precisamos atualizar no psql.
    - No terminal, acesse o psql: psql -h localhost -U pacto academia
    - Atualize o autoincrement dos alunos: SELECT setval('public.alunos_matricula_seq', (SELECT MAX(matricula) FROM alunos) + 1);
    - Atualize o autoincrement dos checkins: SELECT setval('public.checkins_id_seq', (SELECT MAX(id) FROM checkins) + 1);
    - Saia do psql: \q

## 2. Execução e testes da API

1. No Terminal, rode a api através do uvicorn:
    - uvicorn app.main:app --reload
2. Abra um novo terminal e teste os endpoints:
    - Cadastrar um novo aluno: curl -X 'POST'   'http://127.0.0.1:8000/alunos'   -H 'Content-Type: application/json'   -d '{
  "nome": "Paulo",
  "data_nascimento": "1991-09-18",
  "genero": "Masculino",
  "email": "prbs@example.com",
  "plano_id": 1,
  "data_matricula": "2023-02-01",
  "matricula_ativa": true
}'
    - Visualizar todos os alunos: curl -X 'GET' 'http://127.0.0.1:8000/alunos'
    - Realizar checkin: curl -X 'POST' 'http://127.0.0.1:8000/checkins/?aluno_id=1' -H 'accept: application/json'
    - Visualizar todos os checkins: curl -X 'GET' 'http://127.0.0.1:8000/checkins'
    - Visualizar checkin do aluno através do id: curl -X 'GET' 'http://127.0.0.1:8000/checkins/1'
    - Visualizar o churn rate do aluno: curl -X 'GET'   'http://127.0.0.1:8000/churn/1'

# Comentários ao avaliador

- Infelizmente não consegui entregar todas as funcionalidades solicitadas, tive problemas relacionados à minha máquina que demandaram tempo, formatando ela, por exemplo. Mas consegui fazer a API mínima, sem o gerenciamento de filas e também treinei o modelo de previsão de churn.
- Sobre o modelo, Eu estranhei um pouco a boa acurácia. Considerando que usei um script para gerar dados fictícios, pensei que ficaria uma bagunça, por conta da aleatoriedade. Obviamente, para sabermos se ficaria bom mesmo, precisaríamos testar com uma base de dados real.
- Outro viés que notei na churn rate é que ou os resultados estão abaixo de 10% ou acima de 90%. Não encontrei meios termos. Mas pode haver...
- No mais, estou a disposição caso ocorra algum problema na hora de rodar o código e também para tirar dúvidas.