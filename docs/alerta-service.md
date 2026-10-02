# AlertaService — disparo por e-mail

Documentação da issue #47 (RF15, RF16, UC13).

O serviço vive em `backend/app/services/alerta_service.py`. Ele avalia o resultado da análise de preço e envia e-mail via **SMTP** quando as regras de negócio pedem.

## Requisitos cobertos

| ID | Comportamento |
| --- | --- |
| RF15 / RF16 | Disparo de alerta por e-mail |
| UC13 | `avaliarCondicoes(produto, analise)` e `enviarEmail(alerta)` |
| RN07 | Envia se houver queda de **5% ou mais**, ou se o **preço-alvo** for atingido |
| RN08 / RN11 | Não reenvia a mesma ocorrência (mesmo usuário + produto + tipo) dentro do intervalo |

A classificação detalhada da queda (pequena / relevante / grande, RN06) é do `AnaliseService` (issue #43). O `AlertaService` só precisa saber se a queda passa de 5% ou se o alvo foi atingido.

## Como usar

```python
from decimal import Decimal
from app.services.alerta_service import AlertaService, Analise

analise = Analise(
    preco_atual=Decimal("89.90"),
    preco_anterior=Decimal("109.90"),
    queda_percentual=Decimal("18.20"),
    houve_queda_relevante=True,
)
resultado = AlertaService().avaliarCondicoes(produto, analise, db)
```

`avaliarCondicoes` percorre os monitoramentos com `alerta_ativo=True`, envia o e-mail e só então grava `Alerta`. Se o SMTP falhar, o registro **não** é persistido, para o próximo ciclo poder tentar de novo.

## Quando dispara

Para cada monitoramento ativo do produto:

1. **Queda (RN07):** `houve_queda_relevante=True` **ou** `queda_percentual >= 5` **ou** `preco_atual` pelo menos 5% abaixo de `preco_anterior`. Tipo gravado: `queda_preco`.
2. **Preço-alvo (RN07):** `preco_alvo` preenchido e `preco_atual <= preco_alvo`. Tipo gravado: `preco_alvo`.

Os dois podem disparar no mesmo ciclo (são ocorrências diferentes).

## Anti-spam (RN08, RN11)

Se já existe um `Alerta` do **mesmo tipo**, para o **mesmo usuário** e **mesmo produto**, com `data_envio` dentro das últimas `ALERTA_INTERVALO_REENVIOS_HORAS` horas (padrão: 24), o envio é ignorado.

## E-mail

O endereço sai do **Supabase Auth** (`auth.admin.get_user_by_id`), porque a tabela `usuarios` não guarda e-mail. O nome vem de `usuarios.nome`.

O corpo inclui produto, preço e o link de `url_produto`.

## Configuração

Variáveis em `backend/.env`:

| Variável | Padrão | Função |
| --- | --- | --- |
| `ALERTA_QUEDA_MINIMA_PERCENTUAL` | `5` | Limiar da RN07 |
| `ALERTA_INTERVALO_REENVIOS_HORAS` | `24` | Janela sem reenvio (RN08, RN11) |
| `ALERTA_SMTP_DRY_RUN` | `false` | Se `true`, só registra o e-mail no log (útil em desenvolvimento) |
| `SMTP_HOST` | (vazio) | Servidor SMTP |
| `SMTP_PORT` | `587` | Porta |
| `SMTP_USER` / `SMTP_PASSWORD` | (vazio) | Credenciais |
| `SMTP_FROM` | (vazio) | Remetente; se vazio, usa `SMTP_USER` |
| `SMTP_USAR_TLS` | `true` | `STARTTLS` |

Exemplo Gmail (use senha de app, não a senha da conta):

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
SMTP_PASSWORD=senha-de-app
SMTP_FROM=seu-email@gmail.com
SMTP_USAR_TLS=true
```

## Relação com os outros serviços

O `AnaliseService` (issue #43) deve devolver um objeto compatível com `Analise`. O agendador de coleta (veja [coleta-periodica.md](./coleta-periodica.md)) ainda não chama o alerta; quando a análise existir, o fluxo fica: coleta → análise → `avaliarCondicoes`.
