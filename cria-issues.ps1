$repo = "brendaevilly/price-monitor-web-scraping"

# --- Confirme os usernames reais do GitHub de cada pessoa ---
$devops    = "brendaevilly"
$backend   = "anabnovais"
$frontend2 = "jhessjj"
$design    = "KarinePimentel"

# --- Labels e milestone já existem, NAO recriar ---

gh issue create --repo $repo `
  --title "Implementar CRUD de Loja e Produto (RF04, RF05)" `
  --body "Preencher routers/produto.py (hoje vazio). Criar endpoints para cadastrar loja e cadastrar produto monitorado, validando URL e loja identificada antes de salvar (RF05, RN03). Necessario antes do robo de scraping ter algo para coletar." `
  --label "backend" `
  --assignee $backend `
  --milestone "Sprint 2 - Entrega 05/10"

gh issue create --repo $repo `
  --title "Implementar endpoint de login (RF02)" `
  --body "Adicionar rota POST /usuarios/login em routers/usuario.py usando supabase.auth.sign_in_with_password. Retornar o token JWT do Supabase para o frontend armazenar. Cobrir fluxo alternativo 2a (credenciais invalidas) do UC02." `
  --label "backend" `
  --assignee $backend `
  --milestone "Sprint 2 - Entrega 05/10"

gh issue create --repo $repo `
  --title "Implementar AnaliseService - comparacao e identificacao de queda (RF12, RF13)" `
  --body "Preencher services/analise_service.py. Implementar comparacao do preco atual com a coleta anterior e com a media historica (RF12), classificando quedas conforme RN06 (pequena 5-9 por cento, relevante 10-19 por cento, grande 20+ por cento). Nao classificar como queda quando faltarem dados historicos suficientes (RN10). Cobre UC11." `
  --label "backend" `
  --assignee $backend `
  --milestone "Sprint 2 - Entrega 05/10"

gh issue create --repo $repo `
  --title "Implementar endpoint de Monitoramento (RF04, RF14)" `
  --body "Preencher routers/monitoramento.py. Endpoint para o usuario vincular um produto ja cadastrado a sua lista de monitoramento, definindo preco-alvo opcional e ativando/desativando alertas (UC04, UC08)." `
  --label "backend" `
  --assignee $backend `
  --milestone "Sprint 2 - Entrega 05/10"

gh issue create --repo $repo `
  --title "Implementar ColetaService - robo de scraping (RF06, RF07, RF08)" `
  --body "Preencher services/coleta_service.py. Implementar executarColeta(produto) usando BeautifulSoup + Requests para pelo menos 1 site definido no MVP. Deve respeitar intervalo minimo entre requisicoes e limite de tentativas (RNF08), salvar HistoricoPreco em coleta valida, e registrar falha sem apagar historico anterior quando a extracao falhar (UC12, RN09, RN14)." `
  --label "devops,backend" `
  --assignee $devops `
  --milestone "Sprint 2 - Entrega 05/10"

gh issue create --repo $repo `
  --title "Configurar APScheduler para coleta periodica" `
  --body "Configurar o agendamento do ColetaService dentro do proprio servico FastAPI usando APScheduler, rodando em intervalos programados (RF06). Testar que a coleta roda de forma recorrente sem intervencao manual, conforme planejado para o final da Fase 4 do cronograma." `
  --label "devops,backend" `
  --assignee $devops `
  --milestone "Sprint 2 - Entrega 05/10"

gh issue create --repo $repo `
  --title "Implementar AlertaService - disparo de alerta por e-mail (RF15, RF16)" `
  --body "Preencher services/alerta_service.py. Implementar avaliarCondicoes(produto, analise) e enviarEmail(alerta) via SMTP. Disparar quando houver queda relevante (5 por cento+) ou preco-alvo atingido (RN07), evitando reenvio repetido para a mesma ocorrencia dentro do intervalo definido (RN08, RN11). Cobre UC13." `
  --label "devops,backend" `
  --assignee $devops `
  --milestone "Sprint 2 - Entrega 05/10"

gh issue create --repo $repo `
  --title "Atualizar README com instrucoes de execucao e testes manuais (RNF12)" `
  --body "Documentar no README como rodar o projeto via Docker Compose, variaveis de ambiente necessarias, e registrar os testes manuais documentados exigidos pela RNF12 para os fluxos criticos implementados ate aqui." `
  --label "devops" `
  --assignee $devops `
  --milestone "Sprint 2 - Entrega 05/10"

gh issue create --repo $repo `
  --title "Corrigir authService.js e conectar Login/Cadastro a API real (UC01, UC02)" `
  --body "authService.js chama /cadastro e /login, mas o backend expoe /usuarios e /usuarios/login. Corrigir os endpoints e conectar de fato as paginas Login.jsx e Cadastro.jsx (hoje so fazem console.log) ao authService, tratando os fluxos alternativos de erro (e-mail duplicado, credenciais invalidas)." `
  --label "frontend" `
  --assignee $frontend2 `
  --milestone "Sprint 2 - Entrega 05/10"

gh issue create --repo $repo `
  --title "Implementar roteamento real com react-router-dom" `
  --body "Substituir o toggle de estado em App.jsx (useState tela) por react-router-dom de verdade, com rotas para /login, /cadastro, /dashboard e rota protegida que exige autenticacao." `
  --label "frontend" `
  --assignee $frontend2 `
  --milestone "Sprint 2 - Entrega 05/10"

gh issue create --repo $repo `
  --title "Criar tela de cadastro de produto monitorado (UC04)" `
  --body "Formulario para o usuario informar nome, URL do produto, loja e preco-alvo opcional, conectado ao endpoint de Produto/Monitoramento criado no backend." `
  --label "frontend" `
  --assignee $frontend2 `
  --milestone "Sprint 2 - Entrega 05/10"

gh issue create --repo $repo `
  --title "Criar tela de Dashboard (RF19, UC06, UC07, UC09)" `
  --body "Wireframe no Figma + implementacao basica da tela de dashboard: lista de produtos monitorados, historico de precos em ordem cronologica e status dos alertas, consolidados em uma unica tela." `
  --label "design,frontend" `
  --assignee $design `
  --milestone "Sprint 2 - Entrega 05/10"

Write-Host "Todas as issues do Sprint 2 foram criadas!"