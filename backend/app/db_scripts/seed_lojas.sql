-- Lojas do MVP (issue #67). Pode rodar mais de uma vez: ignora domínios já cadastrados.
-- Rode no SQL Editor do Supabase. Equivalente a: python -m app.seed_lojas
INSERT INTO lojas (nome, dominio) VALUES
    ('Mercado Livre', 'mercadolivre.com.br'),
    ('Magazine Luiza', 'magazineluiza.com.br'),
    ('Amazon Brasil', 'amazon.com.br'),
    ('Kabum', 'kabum.com.br'),
    ('Books to Scrape (demo)', 'books.toscrape.com')
ON CONFLICT (dominio) DO NOTHING;
