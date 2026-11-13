$repo = "brendaevilly/price-monitor-web-scraping"

# --- Confirme os usernames reais do GitHub de cada pessoa ---
$devops    = "brendaevilly"
$backend   = "anabnovais"
$frontend2 = "jhessjj"
$design    = "KarinePimentel"

# --- Antes de rodar: crie o milestone no GitHub ---
# Nome exato: Sprint 3 - Entrega 26/10
# Janela: 08/10/2026 a 29/10/2026 | Apresentacao: 26/10/2026 (Fase 6 do cronograma)
# Labels backend, frontend, devops e design ja existem. NAO recriar.

# --- Ja feito na entrega 05/10 (nao reabrir) ---
# RF01/RF02 cadastro e login (API + telas)
# RF03 logout no frontend
# RF04/RF05 loja e produto (API)
# RF06-RF08 ColetaService + APScheduler
# RF12/RF13 AnaliseService (so no backend, sem endpoint)
# RF14 monitoramento PATCH
# RF15/RF16 AlertaService (ainda nao ligado ao agendador)
# RNF12 README e testes manuais
# UC01/UC02/rotas protegidas no frontend
# Dashboard ainda e placeholder; cadastro de produto na UI nao consome a API

gh issue create --repo $repo `
  --title "Expor historico de precos na API (RF10, RF11, UC07)" `
  --body "Criar GET /produtos/{id}/historico para o usuario autenticado. Devolver coletas validas em ordem cronologica, mais preco atual, menor preco e media historica quando houver dados suficientes (RN10). Nao misturar historicos de produtos diferentes e ignorar coletas invalidas (RN09). Necessario para o dashboard e a demonstracao da 3a entrega." `
  --label "backend" `
  --assignee $backend `
  --milestone "Sprint 3 - Entrega 26/10"

gh issue create --repo $repo `
  --title "Expor analise estatistica na API (RF12, RF13, UC11)" `
  --body "Criar GET /produtos/{id}/analise usando o AnaliseService ja implementado. Devolver variacao versus coleta anterior, versus media historica e classificacao (pequena 5-9 por cento, relevante 10-19 por cento, grande 20 por cento+, sem_dados / sem_queda). Nao classificar queda sem amostras suficientes (RN10). Alinha o frontend ao UC11 da 3a entrega de documentacao." `
  --label "backend" `
  --assignee $backend `
  --milestone "Sprint 3 - Entrega 26/10"

gh issue create --repo $repo `
  --title "Remover produto da lista de monitoramento sem apagar historico (RF17, UC05)" `
  --body "Implementar DELETE /monitoramentos/{id} (ou equivalente). O produto some da lista do usuario, novas coletas param se ninguem mais monitorar, e HistoricoPreco permanece (RN05). Nao apagar historico em cascata indevida. Cobre o Should RF17 previsto apos o nucleo da 05/10." `
  --label "backend" `
  --assignee $backend `
  --milestone "Sprint 3 - Entrega 26/10"

gh issue create --repo $repo `
  --title "Listar alertas do usuario autenticado (UC09, UC14)" `
  --body "Criar GET /alertas para o usuario logado, com produto, tipo, data_envio e mensagem. Restringir ao dono (RNF03). Usado pelo dashboard para mostrar alertas disparados e pelo fluxo Receber Alerta (UC14) quando o usuario volta a plataforma." `
  --label "backend" `
  --assignee $backend `
  --milestone "Sprint 3 - Entrega 26/10"

gh issue create --repo $repo `
  --title "Ligar coleta, analise e alerta no APScheduler" `
  --body "Hoje o job so chama ColetaService.executar_coleta_ativos. Depois de cada coleta valida, rodar AnaliseService e AlertaService.avaliarCondicoes para o produto. Nao disparar analise/alerta em coleta invalida (RN09). Fechar o fluxo ponta a ponta scraping -> historico -> comparacao -> e-mail, exigido na apresentacao de 26/10." `
  --label "devops,backend" `
  --assignee $devops `
  --milestone "Sprint 3 - Entrega 26/10"

gh issue create --repo $repo `
  --title "Ampliar scraping para um segundo site do MVP" `
  --body "Cronograma da Fase 6: ampliar o robo para mais produtos/concorrentes. Adicionar extrator de pelo menos 1 loja alem do Mercado Livre (ex. Magazine Luiza, Amazon BR ou Kabum), cadastrar a Loja no banco e garantir que executarColeta identifique o dominio. Manter intervalo minimo e limite de tentativas (RNF08). books.toscrape.com pode continuar so como demo." `
  --label "devops,backend" `
  --assignee $devops `
  --milestone "Sprint 3 - Entrega 26/10"

gh issue create --repo $repo `
  --title "Testes automatizados do fluxo coleta-analise-alerta (RNF12)" `
  --body "Cobrir com pytest o encadeamento: coleta valida gera historico, AnaliseService classifica a queda, AlertaService dispara uma vez e respeita o intervalo de reenvio (RN08, RN11). Usar mocks de HTTP/SMTP. Sem isso a 3a entrega nao fecha o RNF12 nos fluxos novos." `
  --label "backend" `
  --assignee $backend `
  --milestone "Sprint 3 - Entrega 26/10"

gh issue create --repo $repo `
  --title "Tela de cadastro de produto monitorado ligada a API (UC04)" `
  --body "A issue #51 foi encerrada, mas o dashboard local ainda e placeholder. Implementar o formulario (nome, URL, loja, preco-alvo opcional) chamando POST /lojas se preciso e POST /produtos. Tratar URL invalida e loja nao identificada (RF05, RN03, fluxo 3a do UC04). So usuario autenticado." `
  --label "frontend" `
  --assignee $frontend2 `
  --milestone "Sprint 3 - Entrega 26/10"

gh issue create --repo $repo `
  --title "Dashboard com lista, historico e estatisticas (RF09, RF10, RF11, RF19)" `
  --body "Completar /dashboard (UC06, UC07, UC09): listar produtos do usuario (GET /produtos), ao selecionar um item mostrar historico cronologico, preco atual, menor preco, media e classificacao da queda (GET historico e GET analise). Listar alertas recentes. Mensagens em portugues se nao houver dados suficientes (UC07 3a). Responsivo (RNF05)." `
  --label "design,frontend" `
  --assignee $design `
  --milestone "Sprint 3 - Entrega 26/10"

gh issue create --repo $repo `
  --title "Configurar alerta e remover monitoramento na UI (UC05, UC08)" `
  --body "Na lista/detalhe do produto, permitir ativar/desativar alerta e alterar preco-alvo (PATCH /monitoramentos/{id}) e remover o item da lista (DELETE), sem apagar o historico visivel ja coletado. Confirmar remocao. Cobre RF14 e RF17 no frontend." `
  --label "frontend" `
  --assignee $frontend2 `
  --milestone "Sprint 3 - Entrega 26/10"

gh issue create --repo $repo `
  --title "Atualizar Figma do dashboard com historico e analise" `
  --body "Atualizar o Figma para a 3a entrega: card do produto com preco atual / menor / media, lista ou grafico de historico, selo de classificacao de queda (pequena, relevante, grande) e area de alertas. Base para a implementacao da tela de dashboard." `
  --label "design" `
  --assignee $design `
  --milestone "Sprint 3 - Entrega 26/10"

gh issue create --repo $repo `
  --title "Atualizar README e testes manuais da 3a entrega (RNF12)" `
  --body "Documentar no README e em docs/testes-manuais.md (e docs/demonstracao.md) o fluxo da apresentacao de 26/10: cadastrar produto na UI, ver coleta de 2 lojas, historico, analise estatistica e alerta (dry-run ou e-mail). Incluir TM novos para historico, analise, segundo site e remocao de monitoramento." `
  --label "devops" `
  --assignee $devops `
  --milestone "Sprint 3 - Entrega 26/10"

Write-Host "Todas as issues do Sprint 3 (entrega 26/10) foram criadas!"
