# Coleta periódica — APScheduler

Documentação das issues #46 (RF06) e #66 (ciclo completo).

O agendamento roda **dentro do próprio processo FastAPI**. Não é necessário cron, Celery ou intervenção manual: ao subir a API, o APScheduler dispara o ciclo **coleta → histórico → análise → alerta** em intervalo configurável.

## Onde está

| Arquivo | Papel |
| --- | --- |
| `backend/app/scheduler.py` | Job, start/stop e status do agendador |
| `backend/app/main.py` | Liga o scheduler no `lifespan` da API |
| `backend/app/config.py` | Intervalo e flags lidos do `.env` |
| `backend/app/services/ciclo_service.py` | `CicloMonitoramentoService.executar_ciclo(db)` — o que o job chama (#66) |
| `backend/app/services/coleta_service.py` | `executar_coleta_ativos(db, ao_coletar=...)` — coleta e avisa o ciclo a cada produto |

## Como funciona

1. O FastAPI sobe (`uvicorn app.main:app`).
2. O `lifespan` chama `iniciar_agendador()`.
3. O APScheduler registra o job `coleta_periodica` com `IntervalTrigger`.
4. Em cada execução, o job abre uma sessão do banco, chama `CicloMonitoramentoService().executar_ciclo(db)` e fecha a sessão.
5. Ao desligar a API, `parar_agendador()` encerra o scheduler.

O job usa `max_instances=1` e `coalesce=True`: se uma coleta ainda estiver rodando, a seguinte não se sobrepõe; execuções atrasadas viram uma só.

## Fluxo de cada produto (issue #66)

Para cada produto ativo, logo depois da coleta:

```
ColetaService  ->  HistoricoPreco  ->  AnaliseService.classificar  ->  AlertaService.avaliarCondicoes  ->  e-mail (SMTP)
```

| Resultado da coleta | O que acontece |
| --- | --- |
| **Válida** | Roda a análise (UC11) com o histórico válido do produto e, em seguida, `avaliarCondicoes` (UC13) |
| **Inválida** | Só o registro `coleta_valida=False` é gravado. **Não** roda análise nem alerta (RN09) |

Como a análise vira entrada do alerta (`montar_analise_alerta` em `ciclo_service.py`):

- `queda_percentual` é a maior queda positiva entre a comparação com a **média histórica** e com a **coleta anterior** (a RN06 fala em "ou"). Assim a RN07 (queda de 5% ou mais) também funciona enquanto o histórico ainda é curto demais para a média (RN10: mínimo de 3 coletas anteriores).
- `houve_queda_relevante` vale `true` nas faixas queda relevante e grande (10%+).
- O preço-alvo é avaliado pelo `AlertaService` mesmo com histórico curto.
- O anti-spam (RN08/RN11) continua no `AlertaService`: o mesmo alerta não sai de novo dentro de `ALERTA_INTERVALO_REENVIOS_HORAS`.

Se a análise ou o alerta de um produto falhar, o erro vai para o log e o ciclo segue para os demais produtos.

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

Os logs da API registram início e fim de cada ciclo e, por produto, o resultado da análise:

```
Iniciando coleta periódica de produtos ativos.
Coleta válida do produto <id>: R$ 80.00 (tentativa 1)
Produto <id>: grande_queda, 1 alerta(s) enviado(s), 0 ignorado(s).
Coleta periódica concluída: 3 produto(s), 2 válida(s), 2 analisado(s), 1 alerta(s) enviado(s).
```

Para ver o e-mail sem SMTP real, use `ALERTA_SMTP_DRY_RUN=true`: o texto do e-mail aparece no log com o prefixo `[dry-run]`.

## Relação com os serviços

O agendador não extrai preço, não analisa e não envia e-mail: ele só dispara, no tempo certo, o ciclo que encadeia [ColetaService](./coleta-service.md), `AnaliseService` e [AlertaService](./alerta-service.md). Intervalo mínimo entre requisições e limite de tentativas (RNF08) continuam valendo **dentro** de cada ciclo.
