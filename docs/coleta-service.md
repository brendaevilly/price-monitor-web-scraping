# ColetaService — robô de scraping

Documentação da issue #45 (RF06, RF07, RF08).

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

## Site do MVP

O extrator principal é o **Mercado Livre** (`mercadolivre.com` / `mercadolibre.com`).

A loja não fica fixa no código. O serviço escolhe o extrator pelo `dominio` da `Loja` ou, se a loja não vier, pelo hostname de `produto.url_produto`.

Também existem:

- extrator de demonstração para `books.toscrape.com`
- fallback genérico (JSON-LD e meta tags `itemprop` / Open Graph)

Para trocar o site de um produto já cadastrado, atualize `url_produto` e `loja_id`. A próxima coleta usa a loja nova.

Para incluir outro e-commerce, acrescente um extrator e o domínio correspondente em `extrair_preco`. Intervalo, tentativas e persistência continuam iguais.

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
4. Baixa o HTML e tenta extrair o preço. Repete até o limite de tentativas.
5. **Coleta válida:** insere `HistoricoPreco` com `coleta_valida=True`.
6. **Coleta inválida:** insere `HistoricoPreco` com `coleta_valida=False` e **não apaga** registros anteriores. O preço gravado na falha é o último conhecido (ou `0.00` se ainda não houver histórico).

A análise de quedas (issue #43) deve ignorar registros com `coleta_valida=False`.

## Configuração (RNF08)

Variáveis em `backend/.env` (valores padrão já cobrem o MVP):

| Variável | Padrão | Função |
| --- | --- | --- |
| `COLETA_INTERVALO_MINIMO_SEGUNDOS` | `2` | Espera mínima entre requisições |
| `COLETA_MAX_TENTATIVAS` | `3` | Quantas vezes o robô tenta de novo |
| `COLETA_TIMEOUT_SEGUNDOS` | `15` | Tempo máximo de cada HTTP GET |

Elas são lidas em `backend/app/config.py`.

## Extração de preço

Ordem no Mercado Livre:

1. JSON-LD (`application/ld+json`)
2. Meta tags (`itemprop="price"`, `product:price:amount`, `og:price:amount`)
3. Classes `andes-money-amount__fraction` e `andes-money-amount__cents`

O normalizador aceita formatos `R$ 1.299,90`, `1299.90` e `1,299.90`. Preço zero ou negativo é rejeitado.

Se a loja devolver a página de verificação de tráfego (`suspicious-traffic`), a tentativa é tratada como falha e entra no fluxo de `coleta_valida=False`.

## Observação sobre o Mercado Livre

Requisições automáticas podem receber a tela de verificação de tráfego em vez da página do produto. Nesse caso o serviço registra a falha e preserva o histórico.

Para validar o fluxo feliz sem bloqueio, use uma URL de `books.toscrape.com`.
