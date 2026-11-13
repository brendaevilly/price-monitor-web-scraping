-- Issue #105: o frete entra na medição dos preços.
-- Rodar no SQL Editor do Supabase (as tabelas já existem, então o schema.sql não é reexecutado).
-- historico_precos.preco passa a guardar produto + frete; esta coluna guarda só o frete
-- (0 = frete grátis; NULL = a página não informou o frete, caso de todas as coletas antigas).
ALTER TABLE historico_precos ADD COLUMN IF NOT EXISTS frete NUMERIC(10,2);
