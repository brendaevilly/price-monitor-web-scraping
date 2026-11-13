# Entrega\_1\_\_\_PDSI\_1-1

## Página 1

```text

Plataforma para Monitoramento de Preços: Web
         Scraping e Análise Estatı́stica
   Ana Beatriz; Brenda Evilly, Jeslayne Julia e Karine Pimentel
                                  August 2026


Sumário
1 Contexto e Problema                                                              2

2 Público-alvo                                                                    2

3 Escopo e Limites                                                                 3
  3.1 Limites do Projeto . . . . . . . . . . . . . . . . . . . . . . . . . .       5

4 Metodologia de Desenvolvimento                                                   5
  4.1 Abordagem geral . . . . . . . . . . . . . . . . . . . . . . . . . . .        5
  4.2 Divisão de papéis na equipe . . . . . . . . . . . . . . . . . . . . .      5
  4.3 Ferramentas e práticas . . . . . . . . . . . . . . . . . . . . . . . .      6
  4.4 Definição de pronto (Definition of Done) . . . . . . . . . . . . . .       6

5 Riscos e Restrições                                                             7
  5.1 Riscos . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .      7
  5.2 Restrições . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .    8

6 Cronograma                                                                       8
  6.1 Detalhamento do Cronograma . . . . . . . . . . . . . . . . . . . .           9

7 Custos Envolvidos                                                                12

8 Tecnologias Escolhidas                                                    13
  8.1 Stack Técnica e Local de Implantação . . . . . . . . . . . . . . . 13




                                         1

```


---

## Página 2

```text

1     Contexto e Problema
Sites de e-commerce alteram preços com frequência, de acordo com suas próprias
necessidades, como promoções de curta duração, ajustes durante a Black Friday,
igualação de preço com a concorrência, entre outros motivos. Para o consumi-
dor, essas alterações nem sempre são evidentes, geralmente ao ver um preço no
momento da compra, não é possı́vel saber se aquele valor representa uma boa
oportunidade, se o preço pode cair ainda mais, ou se é apenas uma promoção
disfarçada. Essa incerteza vem da falta de comparação de preços ao longo do
tempo na mesma loja, e também entre lojas diferentes.
    Existem algumas ferramentas brasileiras que oferecem propostas similares,
como a Precifica e a InfoPrice, a primeira monitora sites e preços e é integrada a
plataformas de e-commerce, a segunda cobre lojas em todo Brasil monitorando
tanto varejo fı́sico como digital com foco em grandes empresas. Existem softwa-
res internacionais atuantes no brasil, por exemplo Pisync, Mindrest, Price2Spy,
Competera e Lengow. As quatro primeiras monitoram preços e estoque de con-
correntes (via scraping/marketplaces) e ajustam preços automaticamente, com
destaque para Inteligencia Artificial (IA) no caso da Competera, focada em
grandes varejistas. Já o Lengow foge do padrão de scraping puro: combina in-
teligência de mercado com execução multicanal, atuando mais como gestor de
marketplaces do que como monitor de preços.
    Esses concorrentes (principalmente Precifica e os internacionais) já fazem
exatamente o que é proposto aqui, só que como produto comercial maduro,
caro e voltado a médias/grandes empresas. Como projeto acadêmico de um
semestre, o ponto forte não é competir em escala de sites monitorados, e sim:

    • Nicho/escopo menor e mais barato: Minimum Viable Product (MVP) fo-
      cado em poucos concorrentes/e-commerces especı́ficos (ex. nicho de moda,
      eletrônicos), algo que Precifica/InfoPrice não priorizam por serem genera-
      listas de grande escala.
    • Simplicidade de uso para pequeno (lojista, afiliado, dropshipping): Prisync,
      Minderest, Precifica miram médias e grandes operações, um pequeno lo-
      jista muitas vezes não tem orçamento pra essas ferramentas.


2     Público-alvo
    • Persona 1: Pessoas que desejam comprar um produto pelo melhor preço
      possı́vel, mas não têm tempo ou disposição para fazer esse acompanha-
      mento de forma manual. Esse público tem interesse na aplicação porque
      passa a receber alertas de queda de preço automaticamente, sem precisar
      monitorar o site várias vezes por conta própria.
    • Persona 2: Afiliados/criadores de conteúdo (que precisam saber rápido
      quando um preço cai, pra divulgar com mais chance de conversão) e pe-
      quenos lojistas/dropshippers (que hoje não têm acesso a ferramentas de


                                         2

```


---

## Página 3

```text

      monitoramento de concorrência por serem caras, como Prisync e Com-
      petera). Essas duas não entram no MVP, mas justificam a arquitetura
      pensada pra ser extensı́vel no futuro.


3     Escopo e Limites
O escopo deste projeto acadêmico foi delimitado a partir de um MVP restrito
a um nicho e a um número reduzido de e-commerces monitorados. A priori-
dade não é cobrir várias categorias de produto com pouca profundidade, e sim
entregar, com qualidade, o fluxo completo de ponta a ponta: coleta de preços,
armazenamento de histórico, análise, alerta ao usuário.
   A priorização das funcionalidades segue o método MoSCoW, também utili-
zado na definição dos Requisitos Funcionais (Seção 6) e mencionado na análise
de riscos deste documento.

    • MoSCoW: é uma técnica de priorização usada na gestão de projetos e
      produtos. O acrônimo divide tarefas e requisitos em quatro grupos: Must
      have (M), Should have (S), Could have (C) e Won’t have (W).




                                        3

```


---

## Página 4

```text

              Tabela 1: Priorização de funcionalidades (MoSCoW)
 Prioridade          Funcionalidade

 Must                Robô de scraping para coleta periódica de preços em pelo menos um
                     e-commerce, dentro de um nicho definido (ex. eletrônicos).
 Must                Armazenamento do histórico de preços coletados em banco de dados.
 Must                Cadastro e autenticação de usuários.
 Must                Lógica de comparação de preços e disparo automático de alerta
                     (e-mail) quando a queda for relevante.

 Should              Interface web responsiva para consulta do histórico de preços, com
                     visualização gráfica da variação.

 Could               Ampliação do scraping para mais de um nicho ou categoria de produto.
 Could               Notificações via push, além do alerta por e-mail.
 Could               Geração automática de link de afiliado ao identificar uma queda de
                     preço relevante em produto monitorado.

 Won’t (nesta        Monetização direta da plataforma (planos pagos, comissão de afiliado).
 versão)
 Won’t (nesta        Geração automatizada de conteúdo de divulgação (posts, legendas) via
 versão)            IA.
 Won’t (nesta        Dashboard de performance para afiliados (cliques, conversão, receita).
 versão)
 Won’t (nesta        Integração real e autenticada com APIs de plataformas de afiliados
 versão)            (Hotmart, Amazon Associados, Monetizze, Eduzz).
 Won’t (nesta        Aplicativo mobile nativo.
 versão)
 Won’t (nesta        Precificação automática ou negociação com lojas, como fazem
 versão)            concorrentes Business-to-Business (B2B) (ex. Prisync, Competera).
 Won’t (nesta        Camada de análise via RAG, respondendo consultas simples do tipo
 versão)            “esse é um bom momento para comprar X?” com base no histórico
                     coletado.


    Os itens classificados como Should e Could representam o diferencial do
projeto frente aos concorrentes citados na Seção 1, mas só serão desenvolvidos
após a estabilização do núcleo Must, conforme a estratégia de mitigação de risco
descrita na Seção 4.1.




                                          4

```


---

## Página 5

```text

3.1    Limites do Projeto
Os seguintes pontos delimitam o que fica fora do alcance deste trabalho, seja por
restrição de tempo, orçamento ou por não fazerem parte do objetivo acadêmico
da disciplina:

    • O número de e-commerces e produtos monitorados é limitado pela capa-
      cidade de scraping desenvolvida em um semestre, não havendo pretensão
      de cobertura nacional como InfoPrice ou Precifica.

    • O ambiente de hospedagem utiliza serviços em camada gratuita (free tier ),
      sem garantia de disponibilidade contı́nua (SLA) após o encerramento da
      disciplina.
    • Funcionalidades voltadas ao público de afiliados (geração de link, desco-
      berta de produto, dashboard de conversão) ficam registradas como tra-
      balho futuro, servindo para justificar a arquitetura do sistema, mas sem
      integração real obrigatória com plataformas externas de afiliados.
    • O sistema não realiza negociação, ajuste automático de preço ou qual-
      quer ação sobre os sites monitorados — atua apenas como observador e
      informante do consumidor.


4     Metodologia de Desenvolvimento
4.1    Abordagem geral
O desenvolvimento segue uma abordagem ágil de Scrumban ao calendário fixo
de entregas da disciplina de Projeto e Desenvolvimento de Sistemas I (PDSI I),
apresentado na Tabela 3. Cada janela quinzenal de entrega funciona como
um ciclo iterativo (sprint), encerrado com uma apresentação ao professor que
cumpre o papel de sprint review : o grupo mostra o incremento funcional do
sistema e recebe feedback antes de iniciar o ciclo seguinte. Ao mesmo tempo
que adota uma prática de board em que as tarefas são fixadas com estado e
integrantes responsáveis.

4.2    Divisão de papéis na equipe
Com quatro integrantes, a equipe se organiza por área de responsabilidade
técnica, evitando que uma única pessoa concentre conhecimento de uma parte
crı́tica do sistema:




                                        5

```


---

## Página 6

```text

                 Tabela 2: Divisão de responsabilidades técnicas
 Área                           Responsabilidade principal

 Coleta de dados (Web            Implementação e manutenção do robô de coleta, isolado por
 Scraping)                       site em módulos independentes, e do agendamento das
                                 coletas periódicas.
 Histórico e Alertas            Modelagem do histórico de preços no banco de dados,
                                 lógica de comparação de variações e disparo dos alertas ao
                                 usuário.
 Análise Estatı́stica           Definição e implementação das regras estatı́sticas sobre o
                                 histórico coletado (percentual de queda, comparação com a
                                 média histórica) e dos limiares que disparam os alertas.
 Frontend e Cadastro             Interface web, cadastro/autenticação de usuários e exibição
                                 do histórico e das análises ao usuário final.


    Essa divisão é revista a cada ciclo: nas fases finais (ajustes de usabilidade,
ver Tabela de cronograma), integrantes podem apoiar áreas fora da sua respon-
sabilidade principal para garantir as entregas.

4.3      Ferramentas e práticas
   • Controle de versão: Git/GitHub, com uma branch por funcionalidade
     e revisão obrigatória via Pull Request com github Actions antes do merge
     na branch principal.

   • Gestão de tarefas: quadro Scrumban no GitHub Projects, com colunas
     de A fazer, Em andamento, Revisar e Concluı́do.
   • Priorização: método MoSCoW aplicado aos requisitos funcionais, con-
     forme detalhado na Seção 3.
   • Comunicação: alinhamento sı́ncrono curto antes de cada apresentação
     quinzenal, complementado por um canal assı́ncrono (WhatsApp/Discord)
     para dúvidas e bloqueios do dia a dia.
   • Documentação: repositório único do projeto, contendo tanto o código
     quanto este documento, atualizado ao final de cada fase do cronograma.

4.4      Definição de pronto (Definition of Done)
Uma funcionalidade só é considerada concluı́da, e apta a compor uma apre-
sentação, quando atende aos seguintes critérios:

   • Foi testada manualmente pelo integrante responsável e por ao menos um
     outro membro da equipe.


                                         6

```


---

## Página 7

```text

    • Passou por revisão de código (Pull Request) antes do merge.
    • Não interrompe o fluxo principal já existente (scraping → histórico →
      alerta → análise).
    • Está documentada minimamente no repositório (README ou comentários),
      permitindo que outro integrante dê manutenção sem depender de quem
      implementou.


5     Riscos e Restrições
5.1    Riscos
O projeto envolve riscos de natureza técnica, operacional e de escopo, que po-
dem impactar o cronograma e a qualidade do produto final caso não sejam
gerenciados adequadamente.

    • Bloqueio do processo de coleta (scraping): os sites de e-commerce
      monitorados podem alterar a estrutura HTML de suas páginas, adotar
      mecanismos anti-bot (CAPTCHA, rate limiting) ou bloquear o IP uti-
      lizado para a coleta. Esse risco é considerado crı́tico, pois compromete
      diretamente a fonte de dados de todo o sistema. Mitigação: isolar a lógica
      de extração por site em módulos independentes, de modo que uma mu-
      dança em um site não interrompa a coleta dos demais, além de limitar a
      frequência das requisições.
    • Questões legais e de conformidade: alguns sites possuem termos de
      uso que podem restringir a realização de scraping automatizado. Mi-
      tigação: restringir o MVP à coleta de dados públicos de preços, sem coleta
      de dados pessoais, verificar os termos de uso e as polı́ticas de acesso dos
      sites, respeitar as diretrizes estabelecidas no robots.txt e limitar a taxa
      de requisições.
    • Volume insuficiente de dados no curto prazo: por ser um projeto
      acadêmico desenvolvido ao longo de um semestre, o histórico de preços
      coletado pode ser insuficiente para gerar alertas de queda de preço com
      maior confiabilidade. Mitigação: definir um perı́odo mı́nimo de coleta
      para popular o histórico e, quando necessário, utilizar dados históricos
      disponı́veis publicamente ou dados sintéticos para a validação inicial do
      sistema.

    • Complexidade adicional da camada de análise estatı́sticadefinir
      limiares confiáveis para identificar quedas de preço realmente relevantes
      (evitando tanto alertas em excesso quanto a falta deles) exige ajuste fino a
      partir dos dados reais coletados, o que pode consumir mais tempo do que
      o previsto no cronograma. Mitigação: tratar o web scraping e o histórico
      de preços como núcleo obrigatório (Must, no MoSCoW) e a camada de


                                          7

```


---

## Página 8

```text

          análise estatı́stica como incremento posterior (Should /Could ), implemen-
          tada apenas se o núcleo estiver estável.
        • Disponibilidade desigual da equipe: com quatro integrantes e entre-
          gas quinzenais ao longo do semestre, existe o risco de sobreposição com
          atividades de outras disciplinas e de diferenças na disponibilidade dos
          membros da equipe. Mitigação: realizar uma divisão clara de responsabi-
          lidades por entrega e promover alinhamentos rápidos antes de cada data
          de apresentação.

5.2        Restrições
        • Tempo: o cronograma é definido pelo calendário da disciplina PDSI I,
          com datas fixas de entrega e apresentação (ver Seção 6), não havendo
          margem para atrasos sem impacto nas avaliações seguintes.
        • Orçamento: por se tratar de um projeto acadêmico sem orçamento,
          todas as tecnologias e serviços utilizados (banco de dados, hospedagem e
          APIs) devem utilizar, prioritariamente, planos gratuitos (free tier ).
        • Tecnologia: a solução depende de bibliotecas de terceiros para scraping
          e requisições HTTP, cujas mudanças de versão ou descontinuação podem
          exigir ajustes não previstos. Além disso, o desempenho da coleta está
          sujeito aos limites impostos pelos próprios sites monitorados.


6         Cronograma
O cronograma segue as datas oficiais definidas para a disciplina de Projeto e
Desenvolvimento de Sistemas I (PDSI I), apresentadas na Tabela 3.


                  Tabela 3: Cronograma de entregas e apresentações
 Fase                                               Perı́odo               Apresentação

 Apresentação da aplicação             20/08/2026 – 27/08/2026            24/08/2026
 Especificação dos requisitos            27/08/2026 – 03/09/2026            31/08/2026
 Diagrama de casos de uso e de             03/09/2026 – 10/09/2026           10/09/2026
 classes
 1a entrega de implementação             14/09/2026 – 24/09/2026            14/09/2026
    a
 2 entrega de implementação              28/09/2026 – 08/10/2026            05/10/2026
    a
 3 entrega de implementação              08/10/2026 – 29/10/2026            26/10/2026
 4a entrega de implementação             26/10/2026 – 12/11/2026            09/11/2026
 Apresentação final                      16/11/2026 – 03/12/2026            30/11/2026


                                           8

```


---

## Página 9

```text

6.1     Detalhamento do Cronograma
A seguir, o detalhamento interno do grupo dentro de cada janela de entrega,
indicando o que será feito em cada perı́odo.


Tabela 4: Fase 1 — Apresentação da aplicação (20/08 – 27/08/2026 — Apre-
sentação: 24/08/2026)
 Data               Tarefa

 22/08 (sáb)       Revisar o que já está escrito (Contexto e Problema, Público-alvo,
                    Tecnologias Escolhidas) e preparar o material de apresentação da
                    aplicação (proposta, problema, solução e tecnologias).
 23/08 (dom)        Montar os slides da apresentação da aplicação e ensaiar em grupo.
 24/08 (seg)        Apresentação da aplicação.
 25–27/08           Ajustes conforme feedback recebido, antes de iniciar a especificação
                    formal dos requisitos.



Tabela 5: Fase 2 — Especificação dos requisitos (27/08 – 03/09/2026 — Apre-
sentação: 31/08/2026)
 Data               Tarefa

 27/08 (qui)        Iniciar a redação formal dos Requisitos Funcionais (RF) e Não
                    Funcionais (RNF) — usar o robô de scraping, histórico de preços e
                    alertas como base dos RFs.
 28–30/08           Escrever Regras de Negócio, priorizar os requisitos no MoSCoW e
                    definir critérios de aceite de cada um.
 31/08 (seg)        Apresentação da especificação de requisitos.
 01–03/09           Revisão final do documento de requisitos com base no feedback da
                    apresentação.




                                       9

```


---

## Página 10

```text

Tabela 6: Fase 3 — Diagrama de casos de uso e de classes (03/09 – 10/09/2026
— Apresentação: 10/09/2026)
 Data               Tarefa

 03–04/09           Levantar os atores do sistema (usuário, robô de scraping, sistema de
                    alertas/e-mail) e listar os principais casos de uso a partir dos
                    requisitos já definidos.
 05–06/09           Desenhar o diagrama de casos de uso (ex. Draw.io/Lucidchart), com
                    relações de inclusão/extensão entre casos relacionados (ex. “Receber
                    alerta de preço” incluindo “Consultar histórico”).
 07–08/09           Esboçar o diagrama de classes com as entidades principais (Usuário,
                    Produto, Concorrente/Loja, HistoricoPreco, Alerta), atributos e
                    relacionamentos.
 09/09              Revisão cruzada dos dois diagramas entre os membros do grupo,
                    ajustes finais.
 10/09 (qui)        Apresentação dos diagramas de casos de uso e de classes.



Tabela 7: Fase 4 — 1a entrega de implementação (14/09 – 24/09/2026 — Apre-
sentação: 14/09/2026)
 Data               Tarefa

 14/09 (seg)        Apresentação do que já estiver pronto até aqui — trazer ambiente de
                    desenvolvimento configurado e a estrutura inicial do projeto (backend
                    + banco de dados).
 15–18/09           Implementar o robô de scraping para pelo menos 1 e-commerce/nicho
                    definido no MVP, salvando os preços coletados no banco de dados.
 19–24/09           Implementar o modelo de histórico de preços (tabela/schema já
                    definida no diagrama de classes) e testar a coleta rodando de forma
                    recorrente.




                                      10

```


---

## Página 11

```text

Tabela 8: Fase 5 — 2a entrega de implementação (28/09 – 08/10/2026 — Apre-
sentação: 05/10/2026)
 Data               Tarefa

 28/09–01/10        Implementar a lógica de comparação de preços (identificar quedas
                    relevantes) e o disparo de alertas (e-mail ou notificação simples).
 02–04/10           Iniciar o cadastro de usuários (RF01/RF02 do documento de
                    requisitos) e testar o fluxo scraping → histórico → alerta de ponta a
                    ponta.
 05/10 (seg)        Apresentação do scraping, histórico de preços, alertas e cadastro
                    funcionando.
 06–08/10           Ajustes com base no feedback da apresentação.



Tabela 9: Fase 6 — 3a entrega de implementação (08/10 – 29/10/2026 — Apre-
sentação: 26/10/2026)
 Data               Tarefa

 08–15/10           Ampliar o scraping para mais produtos/concorrentes, deixando o
                    histórico de preços mais robusto para dar base à análise estatı́stica.
 16–22/10           Implementar as regras estatı́sticas de análise (ex.: percentual de
                    queda em relação ao preço anterior, comparação com a média
                    histórica do produto) para identificar variações relevantes.
 23–25/10           Preparar a demonstração do sistema com scraping ampliado e as
                    primeiras análises estatı́sticas geradas.
 26/10 (seg)        Apresentação.
 27–29/10           Ajustes com base no feedback recebido.



Tabela 10: Fase 7 — 4a entrega de implementação (26/10 – 12/11/2026 —
Apresentação: 09/11/2026)
 Data               Tarefa

 26/10–02/11        Finalizar a camada de análise estatı́stica (definir os limiares de queda
                    considerados relevantes e a janela de comparação com a média
                    histórica) e conectar ao frontend/relatório de análise.
 03–08/11           Ajustes de usabilidade (responsividade, RNF03) e correção de bugs.
 09/11 (seg)        Apresentação da versão com a análise estatı́stica funcionando.
 10–12/11           Ajustes finais com base no feedback da apresentação.


                                      11

```


---

## Página 12

```text

Tabela 11: Fase 8 — Apresentação final (16/11 – 03/12/2026 — Apresentação:
30/11/2026)
 Data                   Tarefa

 16–21/11               Revisão geral do sistema (scraping, histórico, alertas, análise
                        estatı́stica, cadastro) e testes de carga/performance (RNF01 —
                        resposta em até 2s).
 22–27/11               Preparar a apresentação final (roteiro, slides, demonstração ao vivo) e
                        revisar a documentação entregue ao longo do semestre.
 28–29/11               Ensaio da apresentação em grupo.
 30/11 (seg)            Apresentação final.
 01–03/12               Ajustes finais e fechamento da documentação do semestre.



7       Custos Envolvidos
Por se tratar de um projeto acadêmico sem orçamento financeiro (todas as
tecnologias utilizadas operam em camadas gratuitas, conforme a Seção 5.2), o
principal custo do projeto é o tempo de trabalho da equipe. A Tabela 12 apre-
senta a estimativa de horas programadas por fase, considerando os 4 integrantes
do grupo.


             Tabela 12: Estimativa de horas programadas por fase
 Fase                                           Horas/equipe      Horas/pessoa

 Apresentação da aplicação                       8h                  2h
 Especificação dos requisitos                     12h                  3h
 Diagrama de casos de uso e de                      16h                  4h
 classes
 1a entrega de implementação                      32h                  8h
    a
 2 entrega de implementação                       32h                  8h
    a
 3 entrega de implementação                       40h                  10h
    a
 4 entrega de implementação                       36h                  9h
 Apresentação final                               24h                  6h

 Total estimado                                    200h                 50h

   As fases de implementação (4a à 7a entrega) concentram a maior parte das
horas, por envolverem o desenvolvimento do robô de scraping, do histórico de
preços, dos alertas e da camada de análise estatı́stica. A distribuição de horas


                                           12

```


---

## Página 13

```text

por pessoa é uma média; na prática, cada entrega pode ser dividida de forma de-
sigual entre os integrantes, de acordo com a tarefa técnica de cada um (backend,
scraping, frontend, testes).


8     Tecnologias Escolhidas
Web scraping é a técnica de coletar dados de sites de forma automatizada,
usando um programa (geralmente chamado de “robô”) que acessa páginas web,
lê o código HTML delas e extrai as informações desejadas. O web scraping
neste trabalho resolve o problema construindo, ao longo do tempo, um histórico
de preços que hoje não existe de forma acessı́vel para o consumidor. Um robô
coleta o preço de produtos em e-commerces e armazena essas informações em
um banco de dados, permitindo que o sistema identifique alterações relevantes e
envie alertas ao usuário quando essas alterações forem realmente significativas.
     A análise estatı́stica é a técnica utilizada para transformar o histórico de
preços coletado em informação útil para o usuário, sem depender de modelos
de linguagem ou de infraestrutura de IA. Neste trabalho, a análise é feita a
partir de regras definidas sobre os próprios dados coletados: por exemplo, o
percentual de queda de um produto em relação ao seu preço anterior, ou a
comparação do preço atual com a média histórica registrada para aquele item.
Quando essas regras identificam uma variação relevante, o sistema dispara um
alerta ao usuário, sem a necessidade de consultar uma Application Programming
Interface (API) externa de IA.

8.1    Stack Técnica e Local de Implantação
Esta subseção define as linguagens, frameworks e serviços escolhidos para cada
componente do sistema. O diagrama de componentes e o detalhamento de como
essas tecnologias se conectam serão apresentados na fase de Diagrama de Classes
(Seção 6, Fase 3), respeitando a restrição orçamentária definida na Seção 5.1
(uso prioritário de camadas gratuitas).




                                         13

```


---

## Página 14

```text

                    Tabela 13: Stack técnica por componente
 Componente                  Tecnologia                    Justificativa

 Linguagem principal         Python                        Ecossistema maduro para web
 (backend)                                                 scraping (BeautifulSoup,
                                                           Playwright)
 Framework web/API           FastAPI                       Assı́ncrono, leve, gera
                                                           documentação OpenAPI
                                                           automaticamente a partir dos
                                                           endpoints.
 Coleta de dados             BeautifulSoup +               Cobre tanto páginas estáticas
                             Requests, com Playwright      quanto dinâmicas sem exigir duas
                             para sites com                ferramentas completamente
                             renderização via            distintas.
                             JavaScript
 Agendamento da coleta       APScheduler (dentro do        Evita depender de infraestrutura
                             próprio serviço)            externa paga para cron jobs.
 Banco de dados              PostgreSQL (via               Relacional, adequado ao histórico
                             Supabase)                     de preços com carimbo de tempo; o
                                                           Supabase oferece camada gratuita
                                                           com Postgres, autenticação e a
                                                           extensão pgvector já incluı́da.
 Autenticação              JWT (via Supabase Auth        Simples de integrar ao cadastro de
                             ou biblioteca própria em     usuários sem serviço adicional.
                             FastAPI)
 Envio de alertas            SMTP/biblioteca de            Atende ao requisito de alerta por
                             e-mail transacional           e-mail sem custo para o MVP.
                             (camada gratuita)
 Frontend                    React (com Vite)              Componentização facilita a tela de
                                                           histórico/gráfico de preços e atende
                                                           ao requisito de responsividade.
 Controle de versão e CI    GitHub + GitHub               Já adotado na metodologia
                             Actions                       (Seção 4.3); Actions também é
                                                           usado para automatizar testes a
                                                           cada Pull Request.


Local de implantação. O backend (API e serviço de scraping) é hospedado
em uma plataforma com camada gratuita voltada a aplicações Python (ex. Ren-
der ou Railway); o frontend é publicado separadamente em uma plataforma de
hosting estático (ex. Vercel ou Netlify); e o banco de dados/autenticação/pgvector
ficam centralizados no Supabase. Essa separação por serviço já reflete, em es-
cala reduzida, o princı́pio de implantação independente por componente que


                                        14

```


---

## Página 15

```text

será detalhado na fase de arquitetura.




                                          15

```
