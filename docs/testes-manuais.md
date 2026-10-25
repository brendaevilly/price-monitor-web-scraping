# Testes manuais (RNF12)

Registro dos testes manuais dos fluxos críticos implementados até a Sprint 3. Use este arquivo para marcar data, responsável e resultado.

## Ambiente

- Backend no ar (`uvicorn` ou Docker) em http://127.0.0.1:8000
- `backend/.env` preenchido (Supabase)
- Frontend (TM04 e TM07) em http://127.0.0.1:5173

## TM01 — Health da API

1. Abra http://127.0.0.1:8000/health
2. Confirme JSON com `"status": "ok"`
3. Confirme o objeto `coleta_periodica` (`ativo`, intervalo, `proxima_execucao`)

**Esperado:** API responde sem erro.  
**Resultado:** [ ] passou [ ] falhou  
**Data / quem:**

## TM02 — Cadastro de usuário (UC01)

No Swagger (http://127.0.0.1:8000/docs), `POST /usuarios`:

```json
{
  "nome": "Teste Manual",
  "email": "teste.manual@example.com",
  "senha": "senha1234"
}
```

**Esperado:** HTTP 201 com `id`, `nome`, `email` e `criado_em`. Usuário criado no Supabase Auth e na tabela `usuarios`.  
**Resultado:** [ ] passou [ ] falhou  
**Data / quem:**

## TM03 — E-mail duplicado (fluxo 3a do UC01)

Repita o `POST /usuarios` com o mesmo e-mail do TM02.

**Esperado:** HTTP 409 e mensagem de e-mail já cadastrado.  
**Resultado:** [ ] passou [ ] falhou  
**Data / quem:**

## TM04 — Telas de login e cadastro

1. Abra http://127.0.0.1:5173
2. Preencha o login e envie (ainda só `console.log`)
3. Clique em Cadastre-se, preencha e envie
4. Volte para o login pelo link da tela

**Esperado:** as duas telas renderizam e alternam. A ligação real com a API é a issue #49.  
**Resultado:** [ ] passou [ ] falhou  
**Data / quem:**

## TM05 — Coleta periódica ativa (RF06)

1. Suba o backend com o agendador habilitado (padrão)
2. Chame `GET /health`

**Esperado:** `coleta_periodica.ativo` é `true` e `proxima_execucao` vem preenchida.  
**Resultado:** [ ] passou [ ] falhou  
**Data / quem:**

## TM06 — Recorrência sem intervenção manual

No `backend/.env`:

```env
COLETA_SCHEDULER_INTERVALO_SEGUNDOS=10
COLETA_SCHEDULER_EXECUTAR_NO_STARTUP=true
```

Reinicie a API e observe os logs por ~30 segundos.

**Esperado:** mensagens `Iniciando coleta periódica` / `Coleta periódica concluída` se repetem sozinhas. Se não houver produto ativo, o ciclo ainda roda e registra 0 produto(s).  
**Resultado:** [ ] passou [ ] falhou  
**Data / quem:**

Desligue o intervalo em segundos depois do teste para não martelar as lojas.

## TM07 — Docker Compose

```powershell
docker compose up --build
```

**Esperado:** backend responde em `:8000/health` e frontend abre em `:5173`.  
**Resultado:** [ ] passou [ ] falhou  
**Data / quem:**

## TM08 — Alerta em dry-run (UC13)

1. `ALERTA_SMTP_DRY_RUN=true` no `backend/.env`
2. Com um produto e monitoramento ativos, chame `AlertaService().avaliarCondicoes(produto, analise, db)` (script ou console Python) com queda de 5%+ ou preço-alvo atingido

**Esperado:** log `[dry-run]` com assunto e destinatário; nenhum SMTP real. Reexecução imediata do mesmo tipo não reenvia (RN08, RN11).  
**Resultado:** [ ] passou [ ] falhou  
**Data / quem:**

## TM09 — Histórico de preços do produto (RN09, RN10)

1. Faça login e use **Authorize** no Swagger com o `access_token`
2. Tenha um produto monitorado (`POST /produtos`) e, no Supabase (`historico_precos`), algumas coletas dele, incluindo uma com `coleta_valida = false`
3. `GET /produtos/{id}/historico`

**Esperado:** HTTP 200 só com as coletas válidas, em ordem cronológica, com `preco_atual`, `menor_preco` e `media_historica` (esta fica `null` com menos de 3 coletas anteriores). Produto inexistente ou monitorado só por outro usuário responde 404.  
**Resultado:** [ ] passou [ ] falhou  
**Data / quem:**

## TM10 — Análise de queda (UC11, RN10)

Com os mesmos dados do TM09, chame `GET /produtos/{id}/analise`.

| Coletas anteriores   | Preço atual | Esperado em `classificacao`                   |
| -------------------- | ----------- | --------------------------------------------- |
| 1 a 2                | qualquer    | `sem_dados` (sem média, não classifica queda) |
| 3 ou mais, média 100 | 96          | `sem_queda`                                   |
| 3 ou mais, média 100 | 93          | `pequena_queda`                               |
| 3 ou mais, média 100 | 85          | `queda_relevante`                             |
| 3 ou mais, média 100 | 75          | `grande_queda`                                |

**Esperado:** a resposta traz também `variacao_percentual_media` e `variacao_percentual_anterior` (positivo = queda). Coletas inválidas não entram no cálculo.  
**Resultado:** [ ] passou [ ] falhou  
**Data / quem:**

## TM09 — Ciclo completo coleta → análise → alerta (issue #66)

Pré-requisito: `ALERTA_SMTP_DRY_RUN=true`, `COLETA_SCHEDULER_INTERVALO_SEGUNDOS=30`, `COLETA_SCHEDULER_EXECUTAR_NO_STARTUP=true`, um produto de `books.toscrape.com` monitorado com `alerta_ativo=true` e `preco_alvo` **acima** do preço da página.

1. Suba a API e acompanhe o log.
2. Confirme `Coleta válida do produto ...`, seguida de `Produto ...: <classificação>, N alerta(s) enviado(s)`.
3. Confirme a linha `[dry-run] Alerta preco_alvo para ...` (e-mail simulado).
4. Confirme na tabela `alertas` o registro criado.
5. No ciclo seguinte, o log mostra o alerta como ignorado (anti-spam, RN08/RN11).

**Esperado:** fluxo ponta a ponta sem intervenção manual.  
**Resultado:** [ ] passou [ ] falhou  
**Data / quem:**

## TM10 — Coleta inválida não dispara análise nem alerta (RN09)

Troque a `url_produto` de um produto monitorado para uma página inexistente do mesmo domínio (404) e aguarde um ciclo.

**Esperado:** log `coleta inválida, análise e alerta não executados (RN09)`; nenhum `[dry-run]` e nenhum `Alerta` novo; histórico anterior preservado.  
**Resultado:** [ ] passou [ ] falhou  
**Data / quem:**

## TM11 — Segundo site do MVP: Magazine Luiza (issue #67)

1. Rode `python -m app.seed_lojas` e confirme a loja `magazineluiza.com.br` (via `GET /lojas`).
2. Cadastre um produto com a URL de uma página de produto do Magazine Luiza e a loja correspondente (`POST /produtos`).
3. Aguarde um ciclo ou chame `ColetaService().executarColeta(produto, db)`.

**Esperado:** novo registro em `historico_precos` com o preço da página (`coleta_valida=true`). Se o site bloquear o robô, o registro sai com `coleta_valida=false` e o log explica o motivo.  
**Resultado:** [ ] passou [ ] falhou  
**Data / quem:**

## Testes automatizados

```powershell
cd backend
python -m pytest test -q
```

Cobrem análise, ciclo completo (`test_ciclo_service.py`), extratores por loja (`test_extratores.py`), URLs, lojas, produtos e monitoramentos. Rodam em SQLite em memória, sem Supabase e sem internet.

## TM11 — Parar de monitorar produto (RF17, RN05)

1. Com um produto monitorado e coletas em `historico_precos`, chame `DELETE /monitoramentos/{id}`
2. Chame `GET /produtos`, confira `produtos.ativo` e a contagem de `historico_precos` no Supabase

**Esperado:** HTTP 204; o produto some da lista; `ativo = false` se ninguém mais monitora; histórico intacto. Repetir o DELETE responde 404.  
**Resultado:** [ ] passou [ ] falhou  
**Data / quem:**
