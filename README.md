# PriceBrother

Plataforma de monitoramento de preços via web scraping e análise de dados. Trabalho do bacharelado em Sistemas de Informação (PDSI1).

## Stack

- Backend: Python + FastAPI
- Frontend: React (Vite)
- Banco de dados: PostgreSQL (Supabase)
- Coleta: BeautifulSoup + Requests / Playwright
- Agendamento: APScheduler
- Alertas: SMTP

## Figma

Definição de paletas, tipografia e componentes-base: [Figma](https://www.figma.com/design/rWfjZeqQvwbwf1fHIfCjjX/PriceBrother-%E2%80%94-UI-UX?node-id=0-1&m=dev&t=gSoo01tU4A04bdfV-1)

## Estrutura do repositório

- `backend/` — API, scraping, agendamento e alertas
- `frontend/` — interface web
- `docs/` — documentação dos serviços

Documentação complementar:

- [ColetaService](docs/coleta-service.md)
- [Coleta periódica (APScheduler)](docs/coleta-periodica.md)
- [AlertaService](docs/alerta-service.md)
- [Testes manuais (RNF12)](docs/testes-manuais.md)
- [Manual de demonstração](docs/demonstracao.md)

## Variáveis de ambiente

Copie os exemplos e preencha os valores reais. **Não commite** arquivos `.env`.

### Raiz (`.env`) — Docker Compose

```env
BACKEND_PORT=8000
FRONTEND_PORT=5173
```

### Backend (`backend/.env`)

| Variável | Obrigatória | Função |
| --- | --- | --- |
| `DATABASE_URL` | sim | Connection string do Postgres do Supabase |
| `SUPABASE_URL` | sim | URL do projeto no Supabase |
| `SUPABASE_SECRET_KEY` | sim | Service role key (Project Settings > API) |
| `COLETA_INTERVALO_MINIMO_SEGUNDOS` | não (padrão 2) | Intervalo mínimo entre requisições (RNF08) |
| `COLETA_MAX_TENTATIVAS` | não (padrão 3) | Limite de tentativas da coleta |
| `COLETA_TIMEOUT_SEGUNDOS` | não (padrão 15) | Timeout HTTP da coleta |
| `COLETA_SCHEDULER_HABILITADO` | não (padrão true) | Liga o APScheduler |
| `COLETA_SCHEDULER_INTERVALO_MINUTOS` | não (padrão 60) | Intervalo da coleta periódica |
| `COLETA_SCHEDULER_INTERVALO_SEGUNDOS` | não | Só para teste local; sobrescreve os minutos |
| `COLETA_SCHEDULER_EXECUTAR_NO_STARTUP` | não (padrão false) | Roda a primeira coleta ao subir a API |
| `ALERTA_QUEDA_MINIMA_PERCENTUAL` | não (padrão 5) | Limiar da RN07 |
| `ALERTA_INTERVALO_REENVIOS_HORAS` | não (padrão 24) | Anti-spam de e-mail (RN08, RN11) |
| `ALERTA_SMTP_DRY_RUN` | não (padrão false) | Loga o e-mail sem enviar |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` | para envio real | SMTP dos alertas |
| `SMTP_USAR_TLS` | não (padrão true) | STARTTLS |

### Frontend (`frontend/.env`)

| Variável | Função |
| --- | --- |
| `VITE_API_URL` | URL da API (padrão `http://127.0.0.1:8000`) |
| `VITE_SUPABASE_URL` | URL pública do Supabase |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Chave pública (anon) do Supabase |

## Como rodar

### Docker Compose

Pré-requisitos: [Docker](https://docs.docker.com/get-docker/) e Docker Compose.

```powershell
copy .env.example .env
copy backend\.env.example backend\.env
copy frontend\.env.example frontend\.env
```

Preencha `backend/.env` com Supabase e, se quiser, SMTP. No `.env` da raiz use:

```env
BACKEND_PORT=8000
FRONTEND_PORT=5173
```

Suba os serviços:

```powershell
docker compose up --build
```

- Backend: http://127.0.0.1:8000
- Health: http://127.0.0.1:8000/health
- Swagger: http://127.0.0.1:8000/docs
- Frontend: http://127.0.0.1:5173

Para encerrar: `Ctrl+C` e, se quiser remover os containers, `docker compose down`.

### Backend (local, sem Docker)

Pré-requisito: Python 3.11+ e uma conta no [Supabase](https://supabase.com).

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Preencha `backend/.env` e rode:

```powershell
uvicorn app.main:app --reload
```

- Health check: http://127.0.0.1:8000/health
- Swagger: http://127.0.0.1:8000/docs

### Frontend (local, sem Docker)

Pré-requisito: Node 20+.

```powershell
cd frontend
copy .env.example .env
npm install
npm run dev
```

A interface sobe em http://127.0.0.1:5173. O axios usa `VITE_API_URL` (padrão `http://127.0.0.1:8000`). Login e cadastro falam com `/usuarios` e `/usuarios/login`.

## Testes manuais (RNF12)

Checklist dos fluxos críticos implementados até a Sprint 2. Marque cada item ao validar. Detalhes e evidências esperadas: [docs/testes-manuais.md](docs/testes-manuais.md).

| ID | Fluxo | Como validar | Resultado esperado |
| --- | --- | --- | --- |
| TM01 | Health da API | `GET /health` | `status: ok` e bloco `coleta_periodica` |
| TM02 | Cadastro de usuário (UC01) | `POST /usuarios` no Swagger | `201` com id, nome, e-mail e `criado_em` |
| TM03 | E-mail duplicado (UC01 3a) | Repetir o mesmo e-mail | `409` |
| TM04 | Login e cadastro na API | `/cadastro` e `/login` | Conta criada, token no dashboard, erros 409/401 na tela |
| TM05 | Coleta periódica (RF06) | Subir a API e olhar `/health` | `coleta_periodica.ativo: true` e `proxima_execucao` preenchida |
| TM06 | Recorrência curta | `COLETA_SCHEDULER_INTERVALO_SEGUNDOS=10` e `EXECUTAR_NO_STARTUP=true` | Logs `Iniciando coleta periódica` se repetem |
| TM07 | Docker Compose | `docker compose up --build` | Backend `:8000` e frontend `:5173` sobem |
| TM08 | Alerta dry-run (UC13) | `ALERTA_SMTP_DRY_RUN=true` e chamar `avaliarCondicoes` | Log `[dry-run]` sem SMTP real |

## Modelo de desenvolvimento

- **Branch main**: versão estável e testada do sistema.
- **Branch desenvolvimento**: recebe as integrações e dispara o GitHub Actions.
- **Branch feature/nome**: criada a cada nova integração, a partir de `desenvolvimento`.

**Exemplo**

1. Atribua a issue no Projects e mova para In Progress.
2. Crie `feature/frontend-login` a partir de `desenvolvimento`.
3. Desenvolva e faça commits nela.
4. Abra pull request para `desenvolvimento`. Se o Actions passar e o merge for resolvido, apague a branch feature.

```
git branch          # branches locais
git branch -r       # remotas
git branch -a       # todas
git fetch
git switch nome
git switch -c nome
git switch -c nome origin/nome
git push -u origin nome
git branch -d nome
```

Modelo de escrita dos commits: [Conventional commits](https://www.conventionalcommits.org/en/v1.0.0/)
