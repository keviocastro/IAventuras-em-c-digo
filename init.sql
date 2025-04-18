CREATE TABLE planos (
    id SERIAL PRIMARY KEY,
    duracao INTEGER NOT NULL,
    preco DECIMAL NOT NULL,
    descricao TEXT NOT NULL
);

CREATE TABLE alunos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    cpf VARCHAR(16) NOT NULL UNIQUE,
    plano_id INTEGER NOT NULL REFERENCES planos(id)
);

CREATE TABLE checkins (
    id SERIAL PRIMARY KEY,
    aluno_id INTEGER NOT NULL REFERENCES alunos(id),
    checkin TIMESTAMP,
    checkout TIMESTAMP
);

INSERT INTO planos (duracao, preco, descricao) VALUES
(6, 100.00, 'Plano de 6 meses, cancelamento avulso'),
(12, 80.00, 'Plano de 12 meses, cancelamento com multa de 10% do restante');

INSERT INTO alunos (nome, cpf, plano_id) VALUES
('Aluno 1', '11111111111', 1),
('Aluno 2', '22222222222', 2);

DO $$
DECLARE
    i INTEGER := 0;
    checkin_time TIMESTAMP;
    duration_minutes INTEGER;
    checkout_time TIMESTAMP;
    aluno_id INTEGER;
BEGIN
    WHILE i < 100 LOOP
        aluno_id := CASE WHEN i % 2 = 0 THEN 1 ELSE 2 END;

        checkin_time := NOW() - (TRUNC(RANDOM() * 90) || ' days')::INTERVAL - (TRUNC(RANDOM() * 12) || ' hours')::INTERVAL;

        duration_minutes := FLOOR(RANDOM() * (180 - 30 + 1) + 30);
        checkout_time := checkin_time + (duration_minutes || ' minutes')::INTERVAL;

        INSERT INTO checkins (aluno_id, checkin, checkout)
        VALUES (aluno_id, checkin_time, checkout_time);

        i := i + 1;
    END LOOP;
END $$;
