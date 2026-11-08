-- RN09 / RN14: coleta que falhou não tem preço. Antes, a falha gravava 0.00 (sem
-- histórico) ou repetia o último preço conhecido; agora grava NULL.
-- Rodar no SQL Editor do Supabase ANTES de subir o código novo: sem isto, o
-- INSERT da falha (preco NULL) é recusado pelo NOT NULL e a falha não fica registrada.
-- Pode ser rodado mais de uma vez.

-- 1) preco passa a aceitar NULL (só faz sentido em coleta inválida, ver o CHECK abaixo).
ALTER TABLE historico_precos ALTER COLUMN preco DROP NOT NULL;

-- 2) Limpa o preço das coletas inválidas já gravadas (0.00 ou cópia do último preço).
--    Não mexe em nenhuma coleta válida e não apaga nenhuma linha.
UPDATE historico_precos SET preco = NULL WHERE coleta_valida = false AND preco IS NOT NULL;

-- 3) Garante no banco: coleta válida sempre tem preço positivo.
--    Se este passo falhar, há coleta válida com preço <= 0: corrija antes de repetir.
ALTER TABLE historico_precos DROP CONSTRAINT IF EXISTS ck_historico_preco_valido;
ALTER TABLE historico_precos
    ADD CONSTRAINT ck_historico_preco_valido CHECK (NOT coleta_valida OR (preco IS NOT NULL AND preco > 0));
