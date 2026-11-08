-- RNF01: índice do histórico de preços por produto e data/hora da coleta.
-- Rodar no SQL Editor do Supabase. O schema.sql já traz este índice para bancos
-- novos, mas as tabelas existentes não são recriadas; IF NOT EXISTS torna o
-- script seguro de rodar mais de uma vez.
--
-- Atende as consultas de histórico (GET /produtos/{id}/historico), análise
-- (GET /produtos/{id}/analise), pós-coleta (CicloService) e "última coleta"
-- (ColetaService), todas com WHERE produto_id = ? ORDER BY data_hora_coleta.
CREATE INDEX IF NOT EXISTS idx_historico_produto
    ON historico_precos (produto_id, data_hora_coleta);

-- Índices de apoio já previstos no schema.sql (também idempotentes).
CREATE INDEX IF NOT EXISTS idx_monitoramento_usuario ON monitoramentos (usuario_id);
CREATE INDEX IF NOT EXISTS idx_alerta_usuario        ON alertas (usuario_id);

ANALYZE historico_precos;
