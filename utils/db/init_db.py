from crud import PostgreSQLDatabase

def main():
    db = PostgreSQLDatabase(
        user="postgres",
        dbname="meudb",
        password="senha",
        host="localhost",
        port="5432"
    )

    db.create_db()

    if db.connect_db():
        db.create_table(
            "usuarios",
            """
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100),
            email VARCHAR(100) UNIQUE,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """
        )
        db.create_table(
            "produtos",
            """
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100),
            preco NUMERIC(10,2),
            estoque INT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """
        )
        db.insert("usuarios", {"nome": "Admin", "email": "admin@empresa.com"})

        db.close_db()

if __name__ == "__main__":
    main()
