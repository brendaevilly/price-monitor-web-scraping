-- RNF03 — impede acesso direto às tabelas pela API REST do Supabase (PostgREST).
--
-- Por quê: o frontend leva a chave "publishable" (VITE_SUPABASE_PUBLISHABLE_KEY).
-- Tabelas criadas por SQL (schema.sql) NÃO nascem com Row Level Security. Sem RLS,
-- qualquer pessoa com essa chave consegue ler e alterar usuarios, monitoramentos,
-- alertas etc. direto em https://<projeto>.supabase.co/rest/v1/<tabela>,
-- passando por cima de todas as checagens de dono feitas no backend.
--
-- Como funciona aqui: RLS ligado e SEM políticas = papéis anon/authenticated não
-- enxergam nada. O backend continua funcionando porque usa a conexão direta do
-- Postgres (DATABASE_URL, papel com BYPASSRLS) e a chave service_role.
--
-- ANTES de rodar, confira o estado atual:
--   SELECT relname, relrowsecurity FROM pg_class
--   WHERE relnamespace = 'public'::regnamespace AND relkind = 'r';
-- DEPOIS de rodar, teste login, cadastro de produto e GET /produtos. Se o backend
-- passar a devolver listas vazias/erro, o DATABASE_URL está com um papel sem
-- BYPASSRLS: use a connection string do usuário "postgres".

ALTER TABLE usuarios         ENABLE ROW LEVEL SECURITY;
ALTER TABLE lojas            ENABLE ROW LEVEL SECURITY;
ALTER TABLE produtos         ENABLE ROW LEVEL SECURITY;
ALTER TABLE monitoramentos   ENABLE ROW LEVEL SECURITY;
ALTER TABLE historico_precos ENABLE ROW LEVEL SECURITY;
ALTER TABLE alertas          ENABLE ROW LEVEL SECURITY;
