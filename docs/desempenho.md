# Desempenho das rotas principais (RNF01)

**Meta:** até 2 segundos em condições normais, sem contar o scraping.
Rotas medidas: `POST /usuarios/login`, `GET /produtos`, `GET /produtos/{id}/historico` e `GET /produtos/{id}/analise`.

## O que foi feito

1. **Índice em `historico_precos (produto_id, data_hora_coleta)`**, declarado no modelo (`HistoricoPreco`) com o nome `idx_historico_produto`, o mesmo do `schema.sql`. Como o banco já existe, a migração é `backend/app/db_scripts/migracao_002_indice_historico.sql` (idempotente, rodar no SQL Editor do Supabase).
   Atende todas as consultas do tipo `WHERE produto_id = ? ORDER BY data_hora_coleta`: histórico, análise, pós-coleta (`CicloService`) e "última coleta" (`ColetaService`).
2. **Revisão das consultas** em `routers/produto.py`:
   - histórico e análise passaram a carregar só `preco`, `data_hora_coleta` e `coleta_valida` (linhas leves) em vez de objetos ORM completos;
   - a checagem "o usuário monitora este produto?" (RNF03) virou uma consulta com JOIN, em vez de duas.
   `GET /produtos` já fazia um único JOIN filtrado por `monitoramentos.usuario_id` e não precisou de mudança. Não existe rota de "resumo" separada: o resumo (preço atual, menor preço, média) sai na própria resposta do histórico.
3. **Ferramentas de medição** para a Fase 8:
   - `backend/scripts/medir_tempo_resposta.py`: mede as quatro rotas por HTTP contra uma API no ar (mín, média, p95, máx) e sai com código 1 se algum p95 passar de 2 s;
   - `backend/test/test_desempenho_rotas.py`: teste automatizado (roda no CI) que confere a existência do índice, que a consulta o usa sem sort extra e que as rotas ficam dentro da meta num banco em memória.

## Resultado

Medido em Postgres 16 local, sem latência de rede, rodando as rotas pela aplicação FastAPI (`TestClient`), 20 repetições por rota após aquecimento, p95. Base com **1,5 milhão de linhas** em `historico_precos` (300 produtos com 5.000 coletas cada) e 1 usuário monitorando 30 produtos. O login usa o Supabase Auth, que não existe nesse ambiente: a chamada foi simulada, então o valor mostra só o custo do nosso código.

### Cenário realista: produto com 10.000 coletas

Cerca de 1 ano de coleta de hora em hora (`COLETA_SCHEDULER_INTERVALO_MINUTOS=60`). Os dois lados usam a consulta revisada, para isolar o efeito do índice.

| Rota | Sem índice (p95) | Com índice (p95) | Meta |
|---|---|---|---|
| `POST /usuarios/login` (Auth simulado) | 4 ms | 4 ms | ≤ 2 s |
| `GET /produtos` | 7 ms | 5 ms | ≤ 2 s |
| `GET /produtos/{id}/historico` | 178 ms | 101 ms | ≤ 2 s |
| `GET /produtos/{id}/analise` | 134 ms | 62 ms | ≤ 2 s |

### Cenário de estresse: produto com 200.000 coletas

Base de 1,7 milhão de linhas. Compara o código anterior (sem índice, objetos ORM completos) com o atual (índice + linhas leves).

| Rota | Antes (p95) | Depois (p95) | Meta |
|---|---|---|---|
| `GET /produtos/{id}/historico` | 4.551 ms | 1.908 ms | ≤ 2 s |
| `GET /produtos/{id}/analise` | 5.457 ms | 1.039 ms | ≤ 2 s |

Nesse volume o código anterior estourava a meta; o atual fica dentro dela, embora o histórico fique perto do limite.

### O que os números dizem

- Todas as rotas ficam muito abaixo de 2 s com volumes realistas. O índice troca varredura da tabela inteira por leitura direcionada ao produto.
- Em volumes extremos, o gargalo deixa de ser o banco (o `EXPLAIN ANALYZE` da consulta leva ~85 ms para 200 mil linhas) e passa a ser montar e serializar a lista em Python. Por isso a revisão para linhas leves rendeu mais do que o índice nesse caso.
- O histórico devolve todas as coletas do produto, sem paginação. Se algum produto passar de algumas dezenas de milhares de coletas, vale paginar ou limitar por período.

## Limitações

- Não foi medido contra o Supabase real (sem credenciais aqui). A latência de rede entre a API e o banco soma-se a cada consulta; o login depende também do tempo do Supabase Auth.
- Postgres local, máquina única, sem carga concorrente. Carga com vários usuários simultâneos fica para os testes da Fase 8.

## Como medir no ambiente real

Com a API no ar e um usuário que já monitore produtos com histórico:

```bash
cd backend
python scripts/medir_tempo_resposta.py --url http://127.0.0.1:8000 \
    --email SEU_EMAIL --senha SUA_SENHA --repeticoes 30 --saida ../docs/desempenho-medicao.md
```

Sem credenciais de login, use `--token` com um access token válido (o login aparece como "não medido"). Registre aqui o resultado:

| Data | Ambiente | Coletas no produto | login p95 | produtos p95 | historico p95 | analise p95 | Quem |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

Para aplicar o índice no banco existente, rode `backend/app/db_scripts/migracao_002_indice_historico.sql` no SQL Editor do Supabase e confirme com:

```sql
SELECT indexname FROM pg_indexes WHERE tablename = 'historico_precos';
```
