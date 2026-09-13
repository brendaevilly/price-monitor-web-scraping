-- Usuario (complementa auth.users do Supabase Auth)
CREATE TABLE usuarios (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    nome TEXT NOT NULL,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Loja
CREATE TABLE lojas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome TEXT NOT NULL,
    dominio TEXT NOT NULL
);

-- Produto
CREATE TABLE produtos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome TEXT NOT NULL,
    url_produto TEXT NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT true,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    loja_id UUID NOT NULL REFERENCES lojas(id)
);

-- Monitoramento (classe associativa: Usuario <-> Produto)
CREATE TABLE monitoramentos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    produto_id UUID NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    preco_alvo NUMERIC(10,2),
    alerta_ativo BOOLEAN NOT NULL DEFAULT true,
    data_cadastro TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (usuario_id, produto_id)
);

-- HistoricoPreco (composição: pertence a exatamente um Produto)
CREATE TABLE historico_precos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    produto_id UUID NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    preco NUMERIC(10,2) NOT NULL,
    data_hora_coleta TIMESTAMPTZ NOT NULL DEFAULT now(),
    coleta_valida BOOLEAN NOT NULL DEFAULT true
);

-- Alerta
CREATE TABLE alertas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    produto_id UUID NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL,
    data_envio TIMESTAMPTZ NOT NULL DEFAULT now(),
    mensagem TEXT NOT NULL
);

-- Índices úteis para consultas frequentes (histórico por produto, monitoramentos por usuário)
CREATE INDEX idx_historico_produto ON historico_precos(produto_id, data_hora_coleta);
CREATE INDEX idx_monitoramento_usuario ON monitoramentos(usuario_id);
CREATE INDEX idx_alerta_usuario ON alertas(usuario_id);