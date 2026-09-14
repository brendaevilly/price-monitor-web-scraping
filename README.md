# PriceBrother

## Web Scraping e Análise de Dados

- Trabalho referente ao bacharelado em Sistemas de Informação.

## Stack

- Backend: Python + FastAPI
- Frontend: React (Vite)
- Banco de dados: PostgreSQL (Supabase)
- Coleta: BeautifulSoup + Requests / Playwright
- Agendamento: APScheduler

## Estrutura do repositorio

- \`backend/\` - API e logica de scraping
- \`frontend/\` - Interface web
- \`docs/\` - Documentacao do projeto

## Como rodar

### Backend

Pré-requisito: Python 3.11+ e uma conta no [Supabase](https://supabase.com).

**1. Criar e ativar o ambiente virtual**

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1

```

**2. Instalar as dependências**

```powershell
pip install -r requirements.txt
```

**4. Rodar o servidor**

```powershell
uvicorn app.main:app --reload
```

- Health check: http://127.0.0.1:8000/health
- Documentação interativa (Swagger): http://127.0.0.1:8000/docs

### Modelo de desenvolvimento

- **Branch main**: versão estável e testada do sistema.
- **Branch desenvolvimento**: versão que recebe as integrações feitas no sistema e roda testes no Actions.
- **Branch feature/nome**: criada a cada vez que uma nova integração tem seu desenvolvimento iniciado.

**Exemplo**:

Funcionalidade frontend login tem que ser desenvolvida:

- Atribua a issue frontend login a você no Projects e mova para In Progress.
- Cria branch feature/frontend-login a partir da branch desenvolvimento.
- Desenvolve a funcionalidade e faz commites nela.
- Quando finalizada, faz pull request na branch desenvolvimento, se os testes passarem e o merge resolvido, apaga a branch feature/frontend-login. Se não, resolva, atualize e repita.

```
git branch -> mostra branchs locais.
git branch -r -> mostra branchs remotas.
git branch -a -> mostra todas as branchs.
git fetch -> atualiza infos das branchs.
git switch nome -> troca para branch nome.
git switch -c nome -> cria branch nome e entra.
git switch -c nome origin/nome -> puxa branch remota para local e entra nela.
git push -u origin nome -> envia branch nome para remoto.
git branch -d nome -> apaga branch nome.
```

**Modelo de escrita dos commits:** [Conventional commits](https://www.conventionalcommits.org/en/v1.0.0/)
