# ColetaService — robô de scraping

Documentação das issues #45 (RF06, RF07, RF08) e #67 (segundo site do MVP).

O serviço vive em `backend/app/services/coleta_service.py`. Ele acessa a página do produto com **Requests**, extrai o preço com **BeautifulSoup** e grava um registro em `historico_precos`.

## Requisitos cobertos

| ID | Comportamento |
| --- | --- |
| RF06 | Coleta de preço de produtos ativos (`executar_coleta_ativos`) |
| RF07 | Extração do valor na página do produto |
| RF08 | Persistência do histórico de preços |
| RNF08 | Intervalo mínimo entre requisições e limite de tentativas |
| UC12 | Caso de uso `executarColeta(produto)` |
| RN09 / RN14 | Falha na extração não apaga o histórico anterior |

## Sites suportados

O extrator é escolhido pelo `dominio` da `Loja` do produto (ou, sem loja, pelo hostname de `url_produto`; o `www.` é ignorado). O registro fica em `EXTRATORES`, em `coleta_service.py`.

| Loja | Domínio cadastrado | Ordem de extração | Observação |
| --- | --- | --- | --- |
| Mercado Livre (MVP) | `mercadolivre.com.br` | JSON-LD, meta tags, `.andes-money-amount__*` | Pode devolver tela de verificação de tráfego |
| **Magazine Luiza (MVP)** | `magazineluiza.com.br` | JSON-LD, meta tags, `[data-testid="price-value"]` | Segundo site do MVP (#67) |
| Amazon BR | `amazon.com.br` | JSON-LD, meta tags, `.a-price .a-offscreen` | Costuma pedir captcha para robôs |
| Kabum | `kabum.com.br` | JSON-LD, meta tags, `.finalPrice` | |
| Books to Scrape | `books.toscrape.com` | `.price_color` | Só demonstração |
| Qualquer outra | — | JSON-LD e meta tags (genérico) | Funciona se a loja publicar dados estruturados |

> Os seletores de Magazine Luiza, Amazon BR e Kabum foram escritos a partir da estrutura conhecida dessas páginas e cobertos por testes com HTML de exemplo (`backend/test/test_extratores.py`). Lojas mudam o HTML sem aviso: se uma coleta real falhar com "Preço não encontrado", ajuste o seletor correspondente.

### Cadastrar as lojas no banco

As lojas do MVP são cadastradas de forma idempotente (não duplica):

```powershell
cd backend
python -m app.seed_lojas
```

Ou, direto no SQL Editor do Supabase, rode `backend/app/db_scripts/seed_lojas.sql`. Também é possível cadastrar uma loja pela API (`POST /lojas`).

### Incluir outra loja

1. Escreva `extrair_preco_<loja>(soup, html)` em `coleta_service.py`.
2. Registre um `Extrator(...)` em `EXTRATORES` com os trechos de domínio.
3. Acrescente a loja em `LOJAS_MVP` (`backend/app/seed_lojas.py`) e em `seed_lojas.sql`.
4. Crie um teste em `test_extratores.py` com um HTML de exemplo.

Intervalo, tentativas e persistência continuam iguais (RNF08). O intervalo mínimo é **global**, vale entre quaisquer duas requisições, de qualquer loja.

Para trocar o site de um produto já cadastrado, atualize `url_produto` e `loja_id`. A próxima coleta usa a loja nova.

## Como usar

```python
from app.services.coleta_service import ColetaService

resultado = ColetaService().executarColeta(produto, db)
```

`executarColeta` é o nome do caso de uso. Em Python o método canônico é `executar_coleta`.

Para varrer todos os produtos ativos (entrada do agendador):

```python
resultados = ColetaService().executar_coleta_ativos(db)
```

`executar_coleta_ativos` aceita `ao_coletar(produto, resultado)`, chamado logo após cada coleta. É assim que o ciclo do agendador encadeia análise e alerta (veja [coleta-periodica.md](./coleta-periodica.md)).

A coleta recorrente sem intervenção manual é feita pelo APScheduler. Veja [coleta-periodica.md](./coleta-periodica.md).

### Resultado

`ResultadoColeta` devolve:

- `sucesso` — se a extração encontrou um preço válido
- `produto_id`
- `preco` — valor extraído (ou `None` em falha)
- `coleta_valida`
- `tentativas`
- `historico_id` — registro gravado em `historico_precos`
- `erro` — mensagem quando a coleta falha

## Fluxo

1. Valida se o produto tem URL.
2. Identifica o domínio da loja.
3. Respeita o intervalo mínimo desde a última requisição (RNF08).
4. Baixa o HTML e tenta extrair o preço. Repete até o limite de tentativas. Erros HTTP 4xx permanentes (ex.: 404) não são retentados.
5. **Coleta válida:** insere `HistoricoPreco` com `coleta_valida=True`.
6. **Coleta inválida:** insere `HistoricoPreco` com `coleta_valida=False` e **não apaga** registros anteriores. O preço gravado na falha é o último conhecido (ou `0.00` se ainda não houver histórico).

A análise de quedas (issue #43) ignora registros com `coleta_valida=False`, e o ciclo do agendador não chama análise nem alerta após uma coleta inválida (RN09, issue #66).

## Configuração (RNF08)

Variáveis em `backend/.env` (valores padrão já cobrem o MVP):

| Variável | Padrão | Função |
| --- | --- | --- |
| `COLETA_INTERVALO_MINIMO_SEGUNDOS` | `2` | Espera mínima entre requisições |
| `COLETA_MAX_TENTATIVAS` | `3` | Quantas vezes o robô tenta de novo |
| `COLETA_TIMEOUT_SEGUNDOS` | `15` | Tempo máximo de cada HTTP GET |

Elas são lidas em `backend/app/config.py`.

## Extração de preço

Ordem no Mercado Livre (as outras lojas estão na tabela acima):

1. JSON-LD (`application/ld+json`)
2. Meta tags (`itemprop="price"`, `product:price:amount`, `og:price:amount`)
3. Classes `andes-money-amount__fraction` e `andes-money-amount__cents`

O normalizador aceita formatos `R$ 1.299,90`, `1299.90` e `1,299.90`. Preço zero ou negativo é rejeitado.

Se a loja devolver a página de verificação de tráfego ou de captcha (`suspicious-traffic`, `validateCaptcha` da Amazon), a tentativa é tratada como falha e entra no fluxo de `coleta_valida=False`.

HTTP 404/410 e outros 4xx permanentes abortam na primeira tentativa (não adianta repetir). 408 e 429 ainda entram no limite de tentativas.

## Observação sobre o Mercado Livre

Requisições automáticas podem receber a tela de verificação de tráfego em vez da página do produto. Nesse caso o serviço registra a falha e preserva o histórico.

Para validar o fluxo feliz sem bloqueio, use uma URL de `books.toscrape.com`. Para o Magazine Luiza, use uma URL de página de produto (`.../p/<id>/...`).
