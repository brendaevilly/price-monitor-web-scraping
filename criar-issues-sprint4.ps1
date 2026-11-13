$repo = "brendaevilly/price-monitor-web-scraping"

# --- Confirme os usernames reais do GitHub de cada pessoa ---
$devops    = "brendaevilly"
$backend   = "anabnovais"
$frontend2 = "jhessjj"
$design    = "KarinePimentel"

# --- Antes de rodar: crie o milestone no GitHub ---
# Nome exato: Sprint 4 - Entrega 09/11
# Janela: 26/10/2026 a 12/11/2026 | Apresentacao: 09/11/2026 (Fase 7 do cronograma)
# Labels backend, frontend, devops e design ja existem. NAO recriar.

# --- Ja feito ate a entrega 26/10 (nao reabrir) ---
# RF01-RF03 cadastro, login e logout (API + telas)
# RF04/RF05 loja e produto (API)
# RF06-RF08 ColetaService + APScheduler (agora ligado a analise e alerta)
# RF10/RF11 GET /produtos/{id}/historico
# RF12/RF13 AnaliseService + GET /produtos/{id}/analise
# RF14 monitoramento PATCH; RF17 DELETE /monitoramentos/{id}
# RF15/RF16 AlertaService + GET /alertas
# Segundo site de scraping alem do Mercado Livre
# Testes automatizados do fluxo coleta-analise-alerta
# UC04 tela de cadastro de produto; dashboard com lista, historico e estatisticas
# Configurar alerta / remover monitoramento na UI
# Ajuste: se alguma issue da Sprint 3 ficou aberta, mova para este milestone em vez de duplicar.

gh issue create --repo $repo `
  --title "Definir e parametrizar limiares e janela de comparacao da analise (RF12, RF13, RN06)" `
  --body "Fase 7 do cronograma: finalizar a camada de analise estatistica. Tirar os limiares do codigo e deixar configuraveis (config/env): pequena 5-9 por cento, relevante 10-19 por cento, grande 20 por cento ou mais, e quantidade minima de coletas para comparar (RN06, RN10). Definir a janela de comparacao com a media historica (ex. ultimos N dias ou N coletas) e usar so coletas validas do mesmo produto (RN09, RN10). Documentar os valores escolhidos e o motivo no README." `
  --label "backend" `
  --assignee $backend `
  --milestone "Sprint 4 - Entrega 09/11"

gh issue create --repo $repo `
  --title "Expor janela de analise e resumo geral na API (RF12, RF13, UC11)" `
  --body "Evoluir GET /produtos/{id}/analise para aceitar a janela de comparacao (ex. parametro janela_dias) e devolver variacao versus coleta anterior, versus media da janela e classificacao. Criar GET /analise/resumo com a situacao de todos os produtos do usuario autenticado (classificacao, variacao, preco atual, menor preco) para alimentar o relatorio de analise no frontend. Restringir ao dono (RNF03). Sem dados suficientes, devolver sem_dados e nao classificar queda." `
  --label "backend" `
  --assignee $backend `
  --milestone "Sprint 4 - Entrega 09/11"

gh issue create --repo $repo `
  --title "Testes automatizados da analise com valores conhecidos (RN06-RN08, RNF12)" `
  --body "Cobrir com pytest as faixas e os limites da classificacao: 4,99 / 5 / 9,99 / 10 / 19,99 / 20 por cento, comparacao com coleta anterior e com media da janela, historico insuficiente (sem_dados), coleta invalida ignorada e produtos distintos sem mistura de estatisticas. Cobrir tambem o preco-alvo (RN07) e o intervalo de reenvio de alerta (RN08). Esses testes sao o criterio de aceite RN06-RN08 da especificacao." `
  --label "backend" `
  --assignee $backend `
  --milestone "Sprint 4 - Entrega 09/11"

gh issue create --repo $repo `
  --title "Revisar mensagens de erro, logs e correcao de bugs da API (RF18, RNF06, RNF09)" `
  --body "Levantar bugs encontrados na apresentacao de 26/10 e na demonstracao. Garantir que erros de validacao, autenticacao, coleta e envio de alerta retornem mensagem em portugues e sem detalhes tecnicos sensiveis. Conferir que os logs identificam falhas de autenticacao, coleta, persistencia e envio sem registrar senhas ou tokens. Verificar tambem que usuario nao acessa dados de outro (RNF03)." `
  --label "backend" `
  --assignee $backend `
  --milestone "Sprint 4 - Entrega 09/11"

gh issue create --repo $repo `
  --title "Indices e medicao de tempo de resposta das rotas principais (RNF01)" `
  --body "Criar indice em HistoricoPreco por produto e data/hora da coleta e revisar consultas de historico, analise e resumo. Medir login, GET /produtos, historico e analise e registrar o resultado (meta: ate 2 segundos em condicoes normais, sem contar o scraping). Servira de base para os testes de performance da Fase 8." `
  --label "devops,backend" `
  --assignee $devops `
  --milestone "Sprint 4 - Entrega 09/11"

gh issue create --repo $repo `
  --title "Validar deploy em producao com HTTPS e agendador ativo (RNF04, RNF10)" `
  --body "Conferir backend, frontend e banco publicados em camada gratuita, com HTTPS, variaveis de ambiente corretas (SMTP, JWT, banco) e CORS entre frontend e API. Confirmar que o APScheduler roda em producao encadeando coleta, analise e alerta, e que o free tier nao derruba o servico entre as coletas. Registrar no README como subir e como verificar." `
  --label "devops" `
  --assignee $devops `
  --milestone "Sprint 4 - Entrega 09/11"

gh issue create --repo $repo `
  --title "Robustez da coleta com varias lojas e registro de falhas (RF08, RN14, RNF08)" `
  --body "Revisar o fluxo com as 2 lojas: falha em uma loja nao pode interromper as demais, a falha deve ser registrada sem apagar historico e sem gravar preco zero (RN09, RN14), respeitando intervalo minimo e limite de tentativas (RNF08). Tratar mudanca de HTML retornando erro claro no log. Adicionar teste com HTML alterado simulando a falha." `
  --label "devops,backend" `
  --assignee $devops `
  --milestone "Sprint 4 - Entrega 09/11"

gh issue create --repo $repo `
  --title "Dados de demonstracao e roteiro da apresentacao de 09/11" `
  --body "Mitigar o risco de volume insuficiente de dados: criar script de seed com historico sintetico (claramente marcado como demonstracao) para ter produtos nas tres faixas de queda (pequena, relevante, grande) e um sem dados suficientes. Montar o roteiro da demonstracao: cadastro de produto, coleta de 2 lojas, historico com grafico, analise por janela, relatorio e alerta (dry-run ou e-mail). Ensaiar o fluxo completo antes de 09/11." `
  --label "devops" `
  --assignee $devops `
  --milestone "Sprint 4 - Entrega 09/11"

gh issue create --repo $repo `
  --title "Mostrar analise estatistica no dashboard com janela de comparacao (RF12, RF13, UC11)" `
  --body "No detalhe do produto, exibir variacao versus coleta anterior e versus media, selo de classificacao (pequena, relevante, grande, sem queda) e seletor da janela de comparacao consumindo GET /produtos/{id}/analise. Quando nao houver dados suficientes, mostrar mensagem em portugues e nao exibir selo de queda (UC07 3a, UC11 3a). Tratar loading e erro de API." `
  --label "frontend" `
  --assignee $frontend2 `
  --milestone "Sprint 4 - Entrega 09/11"

gh issue create --repo $repo `
  --title "Grafico de historico de precos com media e preco-alvo (RF10, RF11, Should)" `
  --body "Adicionar ao dashboard um grafico de linha do historico cronologico (coletas validas) com linha da media da janela e do preco-alvo quando existir, alem de preco atual e menor preco. Escolher biblioteca leve compativel com React/Vite. Deve funcionar em tela de celular e lidar com historico vazio ou com um unico ponto." `
  --label "frontend" `
  --assignee $frontend2 `
  --milestone "Sprint 4 - Entrega 09/11"

gh issue create --repo $repo `
  --title "Relatorio de analise com resumo de todos os produtos (RF12, RF13, RF19)" `
  --body "Criar a tela ou secao de relatorio de analise consumindo GET /analise/resumo: tabela/cards com produto, loja, preco atual, variacao e classificacao, com filtro por faixa de queda e ordenacao pela maior queda. Ligar cada linha ao detalhe do produto no dashboard. Apenas usuario autenticado (RN02)." `
  --label "frontend" `
  --assignee $frontend2 `
  --milestone "Sprint 4 - Entrega 09/11"

gh issue create --repo $repo `
  --title "Responsividade e ajustes de usabilidade das telas (RNF05, RNF06)" `
  --body "Revisar login, cadastro, dashboard, cadastro de produto e relatorio em celular, tablet e computador. Corrigir quebras de layout, areas de toque pequenas e rolagem horizontal. Garantir que todos os textos de interface, validacao e erro estejam em portugues e claros. Aplicar os ajustes definidos na revisao de usabilidade do design." `
  --label "frontend" `
  --assignee $frontend2 `
  --milestone "Sprint 4 - Entrega 09/11"

gh issue create --repo $repo `
  --title "Atualizar Figma: relatorio, grafico, estados vazios e versoes mobile" `
  --body "Atualizar o Figma para a 4a entrega: tela de relatorio de analise, grafico de historico com media e preco-alvo, selo de classificacao, estados vazios (sem dados suficientes, sem produtos, sem alertas), estados de erro e carregamento, e versoes mobile e tablet das telas principais. Base para a implementacao do frontend." `
  --label "design" `
  --assignee $design `
  --milestone "Sprint 4 - Entrega 09/11"

gh issue create --repo $repo `
  --title "Revisao de usabilidade com teste rapido e lista de ajustes (RNF05, RNF06)" `
  --body "Fazer um teste rapido com 2 ou 3 pessoas fora do grupo (cadastrar produto, ver analise, configurar alerta) e uma revisao heuristica das telas. Registrar problemas encontrados por prioridade e abrir/atualizar as issues de frontend correspondentes. Prazo de 03 a 08/11, conforme a Fase 7." `
  --label "design,frontend" `
  --assignee $design `
  --milestone "Sprint 4 - Entrega 09/11"

gh issue create --repo $repo `
  --title "Atualizar README e testes manuais da 4a entrega (RNF12)" `
  --body "Documentar no README, em docs/testes-manuais.md e em docs/demonstracao.md o fluxo da apresentacao de 09/11: analise estatistica com limiares e janela definidos, grafico, relatorio de analise e alerta. Incluir TM novos para janela de comparacao, historico insuficiente, relatorio, responsividade e falha de coleta em uma loja. Registrar os limiares escolhidos e a justificativa." `
  --label "devops" `
  --assignee $devops `
  --milestone "Sprint 4 - Entrega 09/11"

Write-Host "Todas as issues do Sprint 4 (entrega 09/11) foram criadas!"