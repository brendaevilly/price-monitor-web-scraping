-- Rodar no SQL Editor do Supabase (as tabelas já existem, então o schema.sql não é reexecutado).
-- Garante no banco o que os endpoints já checam no código (evita duplicatas em requisições simultâneas).
-- Se der erro por duplicatas já existentes, remova-as antes de rodar.
ALTER TABLE lojas    ADD CONSTRAINT uq_lojas_dominio        UNIQUE (dominio);
ALTER TABLE produtos ADD CONSTRAINT uq_produtos_url_produto UNIQUE (url_produto);
