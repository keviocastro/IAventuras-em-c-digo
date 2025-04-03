# Este script representa apenas exemplos de uso da minha implementação do banco de dados

from utils.db.crud import PostgreSQLDatabase
from config.constants import EnvVars

env = EnvVars()
db_password = env.get_var("DB_PASSWORD")

db = PostgreSQLDatabase(
    user="juanml",
    dbname="churnml",
    password=db_password,
    host="localhost",
    port="5432"
)

# db.create_db()

if db.connect_db():
    # apenas um exemplo, as tabelas principais já foram criadas
    # db.create_table(
    #     "usuarios", 
    #     """
    #     id SERIAL PRIMARY KEY,
    #     nome VARCHAR(100) NOT NULL,
    #     email VARCHAR(100) UNIQUE NOT NULL,
    #     idade INTEGER,
    #     data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    #     """
    # )
    
    db.insert("alunos", {
        "nome_aluno": "João",
        "idade_aluno": 29
    })
    
    db.insert("alunos", {
        "nome_aluno": "Maria",
        "idade_aluno": 29
    })
    
    print("\nTodos os alunos:")
    alunos = db.read("alunos")
    for aluno in alunos:
        print(aluno)
    
    print("\nAluno com id_aluno=1:")
    aluno = db.read("alunos", condition="id_aluno = 1")
    print(aluno)
    
    db.update_table(
        "alunos", 
        {"nome_aluno": "João Atualizado", "idade_aluno": 31},
        "id_aluno = 1"
    )
    
    print("\nAluno após atualização:")
    aluno = db.read("alunos", condition="id_aluno = 1")
    print(aluno)
    
    db.delete("alunos", "id_aluno = 2")
    
    print("\nTodos os alunos após exclusão:")
    alunos = db.read("alunos")
    for aluno in alunos:
        print(aluno)
    
    db.close_db()