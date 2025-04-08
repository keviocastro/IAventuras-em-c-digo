CREATE TABLE planos (
    id SERIAL PRIMARY KEY,
    plano_nome VARCHAR(100) NOT NULL
);

CREATE TABLE alunos (
    id SERIAL PRIMARY KEY,
    aluno_status VARCHAR(20) DEFAULT 'ativo' CHECK (aluno_status IN ('ativo', 'inativo')),
    plano_id INTEGER REFERENCES planos(id)
);

CREATE TABLE checkins (
    id SERIAL PRIMARY KEY,
    aluno_id INTEGER REFERENCES alunos(id) NOT NULL,
    data_entrada TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duracao_treino INTEGER -- em minutos
);

-- Criação dos índices
CREATE INDEX idx_alunos_plano ON alunos(plano_id);
CREATE INDEX idx_checkins_aluno ON checkins(aluno_id);
CREATE INDEX idx_checkins_data ON checkins(data_entrada);


-- Rodar update_db.py para popular o banco de dados com dados de exemplo substanciais


-- -- Inserindo dados na tabela 'planos'
-- INSERT INTO planos (plano_nome) VALUES
--     ('Bronze'),
--     ('Prata'),
--     ('Ouro');

-- -- Inserindo dados na tabela 'alunos'
-- INSERT INTO alunos (aluno_status, plano_id) VALUES
--     ('ativo', 1),
--     ('inativo', 2),
--     ('ativo', 3),
--     ('inativo', 1),
--     ('ativo', 2),
--     ('ativo', 3),
--     ('ativo', 1),
--     ('ativo', 2),
--     ('ativo', 3),
--     ('ativo', 1);

-- -- Inserindo dados na tabela 'checkins'
-- INSERT INTO checkins (aluno_id, data_entrada, duracao_treino) VALUES
--     (1, '2025-04-02 08:00:00', 60),
--     (1, '2025-04-04 08:00:00', 90),
--     (2, '2025-04-01 10:00:00', 75),
--     (2, '2025-04-05 10:00:00', 71),
--     (3, '2025-04-01 12:00:00', 63),
--     (4, '2025-04-01 14:00:00', 45),
--     (4, '2025-04-03 14:00:00', 100),
--     (5, '2025-04-01 16:00:00', 62),
--     (5, '2025-04-07 16:00:00', 90),
--     (6, '2025-04-03 18:00:00', 90),
--     (7, '2025-04-01 20:00:00', 60),
--     (7, '2025-04-03 20:00:00', 90),
--     (8, '2025-04-01 22:00:00', 60),
--     (9, '2025-04-02 08:00:00', 60),
--     (9, '2025-04-04 08:00:00', 90),
--     (10, '2025-04-02 10:00:00', 60),
--     (10, '2025-04-04 10:00:00', 90);