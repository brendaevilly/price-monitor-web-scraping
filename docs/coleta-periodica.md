# Coleta periódica — APScheduler

Documentação da issue #46 (RF06).

O agendamento roda **dentro do próprio processo FastAPI**. Não é necessário cron, Celery ou intervenção manual: ao subir a API, o APScheduler dispara o `ColetaService` em intervalo configurável.

## Onde está

| Arquivo | Papel |
| --- | --- |
| `backend/app/scheduler.py` | Job, start/stop e status do agendador |
| `backend/app/main.py` | Liga o scheduler no `lifespan` da API |
| `backend/app/config.py` | Intervalo e flags lidos do `.env` |
| `backend/app/services/coleta_service.py` | `executar_coleta_ativos(db)` — o que o job chama |

## Como funciona

1. O FastAPI sobe (`uvicorn app.main:app`).
2. O `lifespan` chama `iniciar_agendador()`.
3. O APScheduler registra o job `coleta_periodica` com `IntervalTrigger`.
4. Em cada execução, o job abre uma sessão do banco, chama `ColetaService().executar_coleta_ativos(db)` e fecha a sessão.
5. Ao desligar a API, `parar_agendador()` encerra o scheduler.

O job usa `max_instances=1` e `coalesce=True`: se uma coleta ainda estiver rodando, a seguinte não se sobrepõe; execuções atrasadas viram uma só.

## Configuração

Variáveis em `backend/.env`:

| Variável | Padrão | Função |
| --- | --- | --- |
| `COLETA_SCHEDULER_HABILITADO` | `true` | Liga ou desliga o agendador |
| `COLETA_SCHEDULER_INTERVALO_MINUTOS` | `60` | Intervalo de produção (RF06) |
| `COLETA_SCHEDULER_INTERVALO_SEGUNDOS` | (vazio) | Se preenchido, sobrescreve o intervalo em minutos — só para teste local |
| `COLETA_SCHEDULER_EXECUTAR_NO_STARTUP` | `false` | Se `true`, a primeira coleta roda assim que a API sobe |

Exemplo para observar recorrência sem esperar 60 minutos:

```env
COLETA_SCHEDULER_INTERVALO_SEGUNDOS=10
COLETA_SCHEDULER_EXECUTAR_NO_STARTUP=true
```

## Como conferir que está ativo

Health check:

```
GET http://127.0.0.1:8000/health
```

Resposta esperada (campos principais):

```json
{
  "status": "ok",
  "coleta_periodica": {
    "ativo": true,
    "intervalo_minutos": 60,
    "intervalo_segundos": null,
    "proxima_execucao": "2026-10-01T23:30:00-03:00"
  }
}
```

Os logs da API registram início e fim de cada ciclo (`Iniciando coleta periódica` / `Coleta periódica concluída`).

## Relação com o ColetaService

O agendador não extrai preço. Ele só dispara, no tempo certo, o serviço documentado em [coleta-service.md](./coleta-service.md). Intervalo mínimo entre requisições e limite de tentativas (RNF08) continuam valendo **dentro** de cada ciclo.
