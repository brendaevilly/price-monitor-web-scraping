# Testes manuais (RNF12)

Registro dos testes manuais dos fluxos críticos implementados até a Sprint 2. Use este arquivo para marcar data, responsável e resultado.

## Ambiente

- Backend no ar (`uvicorn` ou Docker) em http://127.0.0.1:8000
- `backend/.env` preenchido (Supabase)
- Frontend (TM04 e TM07) em http://127.0.0.1:5173

## TM01 — Health da API

1. Abra http://127.0.0.1:8000/health
2. Confirme JSON com `"status": "ok"`
3. Confirme o objeto `coleta_periodica` (`ativo`, intervalo, `proxima_execucao`)

**Esperado:** API responde sem erro.  
**Resultado:** [ ] passou  [ ] falhou  
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
**Resultado:** [ ] passou  [ ] falhou  
**Data / quem:**

## TM03 — E-mail duplicado (fluxo 3a do UC01)

Repita o `POST /usuarios` com o mesmo e-mail do TM02.

**Esperado:** HTTP 409 e mensagem de e-mail já cadastrado.  
**Resultado:** [ ] passou  [ ] falhou  
**Data / quem:**

## TM04 — Telas de login e cadastro

1. Abra http://127.0.0.1:5173
2. Preencha o login e envie (ainda só `console.log`)
3. Clique em Cadastre-se, preencha e envie
4. Volte para o login pelo link da tela

**Esperado:** as duas telas renderizam e alternam. A ligação real com a API é a issue #49.  
**Resultado:** [ ] passou  [ ] falhou  
**Data / quem:**

## TM05 — Coleta periódica ativa (RF06)

1. Suba o backend com o agendador habilitado (padrão)
2. Chame `GET /health`

**Esperado:** `coleta_periodica.ativo` é `true` e `proxima_execucao` vem preenchida.  
**Resultado:** [ ] passou  [ ] falhou  
**Data / quem:**

## TM06 — Recorrência sem intervenção manual

No `backend/.env`:

```env
COLETA_SCHEDULER_INTERVALO_SEGUNDOS=10
COLETA_SCHEDULER_EXECUTAR_NO_STARTUP=true
```

Reinicie a API e observe os logs por ~30 segundos.

**Esperado:** mensagens `Iniciando coleta periódica` / `Coleta periódica concluída` se repetem sozinhas. Se não houver produto ativo, o ciclo ainda roda e registra 0 produto(s).  
**Resultado:** [ ] passou  [ ] falhou  
**Data / quem:**

Desligue o intervalo em segundos depois do teste para não martelar as lojas.

## TM07 — Docker Compose

```powershell
docker compose up --build
```

**Esperado:** backend responde em `:8000/health` e frontend abre em `:5173`.  
**Resultado:** [ ] passou  [ ] falhou  
**Data / quem:**

## TM08 — Alerta em dry-run (UC13)

1. `ALERTA_SMTP_DRY_RUN=true` no `backend/.env`
2. Com um produto e monitoramento ativos, chame `AlertaService().avaliarCondicoes(produto, analise, db)` (script ou console Python) com queda de 5%+ ou preço-alvo atingido

**Esperado:** log `[dry-run]` com assunto e destinatário; nenhum SMTP real. Reexecução imediata do mesmo tipo não reenvia (RN08, RN11).  
**Resultado:** [ ] passou  [ ] falhou  
**Data / quem:**
