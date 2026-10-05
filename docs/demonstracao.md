# Manual de demonstração

Como subir o sistema e mostrar o que já está implementado (Sprint 2 + issues #49 e #50).

## 1. Subir o ambiente

No terminal, na raiz do repositório:

**Backend**

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Confirme `backend/.env` com `DATABASE_URL`, `SUPABASE_URL` e `SUPABASE_SECRET_KEY`.

**Frontend** (outro terminal)

```powershell
cd frontend
npm install
npm run dev
```

Abra:

- Interface: http://127.0.0.1:5173
- Health: http://127.0.0.1:8000/health
- Swagger: http://127.0.0.1:8000/docs

No Supabase, desative a confirmação obrigatória de e-mail se quiser entrar logo após o cadastro (Authentication > Providers > Email).

## 2. Autenticação e rotas (issues #49 e #50)

### Cadastro (UC01)

1. Abra http://127.0.0.1:5173/cadastro
2. Preencha nome, e-mail novo e senha com 8+ caracteres
3. Clique em **Cadastrar**
4. A API responde `POST /usuarios` (`201`)
5. O app redireciona para `/login` com a mensagem de conta criada

**Erro para mostrar:** cadastre o mesmo e-mail de novo. A tela deve exibir *Já existe um usuário cadastrado com este e-mail* (`409`).

### Login (UC02)

1. Em `/login`, entre com a conta criada
2. A API responde `POST /usuarios/login` (`200`) com `access_token`
3. O token fica no `localStorage` (`pb_access_token`)
4. O app vai para `/dashboard` e mostra o nome do usuário

**Erro para mostrar:** senha errada. A tela deve exibir *E-mail ou senha incorretos* (`401`).

### Rota protegida

1. Clique em **Sair** — volta para `/login` e some o token
2. Digite na barra http://127.0.0.1:5173/dashboard sem estar logado — deve ir para `/login`
3. Depois de logar, `/` e `/login` levam ao dashboard

Rotas: `/login`, `/cadastro`, `/dashboard` (protegida). Quem não está autenticado não vê o dashboard.

## 3. API no Swagger

Em http://127.0.0.1:8000/docs:

| O quê | Como |
| --- | --- |
| Health + agendador | `GET /health` — `status: ok` e `coleta_periodica.ativo` |
| Cadastro | `POST /usuarios` |
| Login | `POST /usuarios/login` — copie o `access_token` |
| Autorizar as outras rotas | Authorize no Swagger: `Bearer <token>` |
| Loja | `POST /lojas` |
| Produto | `POST /produtos` (URL válida da loja) |
| Monitoramento | `POST /monitoramentos` e `PATCH /monitoramentos/{id}` |

## 4. Coleta periódica (RF06)

1. `GET /health` deve trazer `proxima_execucao`
2. Para ver o job repetir nos logs da API, no `backend/.env`:

```env
COLETA_SCHEDULER_INTERVALO_SEGUNDOS=10
COLETA_SCHEDULER_EXECUTAR_NO_STARTUP=true
```

3. Reinicie o uvicorn. Aparecem `Iniciando coleta periódica` e `Coleta periódica concluída` sem clicar em nada
4. Depois do demo, apague o intervalo em segundos para não martelar as lojas

Com produto ativo (URL de `books.toscrape.com` funciona melhor que Mercado Livre), o `ColetaService` grava `historico_precos`.

## 5. Análise e alerta (serviço)

Ainda não há tela. Dá para mostrar no código ou num console Python, com o backend no ar:

1. Depois de duas coletas válidas, o `AnaliseService` classifica a queda (5–9% pequena, 10–19% relevante, 20%+ grande)
2. `AlertaService.avaliarCondicoes` dispara e-mail se a queda for 5%+ ou o preço-alvo for atingido
3. Para demo sem SMTP: `ALERTA_SMTP_DRY_RUN=true` — o log mostra `[dry-run]`
4. O mesmo tipo não reenvia nas 24 h seguintes (RN08, RN11)

## 6. Docker Compose (opcional)

```powershell
copy .env.example .env
copy backend\.env.example backend\.env
copy frontend\.env.example frontend\.env
```

Preencha o `backend/.env` e rode `docker compose up --build`. Backend em `:8000`, frontend em `:5173`.

## 7. Roteiro curto (3–5 minutos)

1. Health no navegador
2. Cadastro pela interface → login → dashboard
3. E-mail duplicado e senha errada
4. Sair e tentar abrir `/dashboard` (bloqueado)
5. Swagger: login, authorize, criar loja/produto/monitoramento
6. Logs da coleta periódica

## O que ainda não tem tela

- Cadastro de produto/monitoramento no frontend (issue #51)
- Dashboard com histórico e alertas (issue #52)
- Esses fluxos se demonstram no Swagger até as telas existirem
