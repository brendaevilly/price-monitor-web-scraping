-- Issue #104: o mesmo produto monitorado em mais de uma loja.
-- Rodar no SQL Editor do Supabase (as tabelas já existem, então o schema.sql não é reexecutado).
-- Cada oferta (loja + URL) continua sendo uma linha de `produtos`, com histórico próprio;
-- as ofertas do mesmo item dividem o mesmo grupo_id (NULL = produto de uma loja só).
ALTER TABLE produtos ADD COLUMN IF NOT EXISTS grupo_id UUID;
CREATE INDEX IF NOT EXISTS ix_produtos_grupo_id ON produtos (grupo_id);
