# Mais de uma loja por produto (issue #104)

O robô passa a procurar o mesmo produto em várias lojas. Cada oferta (loja + URL) continua sendo
um `Produto`, com histórico, análise e alerta próprios, então o ciclo de coleta já o cobre sem
mudança. As ofertas do mesmo item dividem o `grupo_id` (`NULL` = uma loja só).

## Endpoints

| Rota | O que faz |
|---|---|
| `POST /produtos` | Aceita `outras_lojas: [{loja_id, url_produto, nome?, preco_alvo?}]` (até 5). Tudo é salvo junto ou nada. |
| `POST /produtos/{id}/lojas` | Acrescenta uma loja a um produto que o usuário já monitora. Herda nome e preço-alvo do original, se não informados. |
| `GET /produtos/{id}/lojas` | Comparativo entre as lojas que o usuário monitora: último preço válido (já com frete, #105), frete, menor preço visto, `melhor_oferta` e `economia`. |

Regras: cada loja só aparece uma vez por produto (422/409); a URL precisa pertencer à loja (RN03); só
coletas válidas entram no comparativo (RN09); só aparecem as ofertas que o próprio usuário monitora (RNF03).

## Banco existente

Rode `backend/app/db_scripts/migracao_004_grupo_lojas.sql` no SQL Editor do Supabase.
Bancos novos já têm a coluna no `schema.sql`.
