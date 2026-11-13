# Entrega\_4\_\_\_PDSI\_1-1

## Página 1

```text

                    Diagrama de Classes: PriceBrother
      Ana Beatriz       Brenda Evilly       Jeslayne Julia   Karine Pimentel

                                  September 2026


Sumário
1 Introdução                                                                   2

2 Diagrama de Classes                                                          2

3 Descrição das Classes                                                        3

4 Rastreabilidade com Casos de Uso                                             6




                                        1

```


---

## Página 2
![Figura da página 2](https://private-us-east-1.manuscdn.com/sessionFile/2BSNzswJjzScGcdnGdr3FM/sandbox/dcq2zwtQYnruevyREEZY8g-images_1791162498200_na1fn_L2hvbWUvdWJ1bnR1L3dvcmsvcGRzaS9tYXJrZG93bi9hc3NldHMvRW50cmVnYV80X19fUERTSV8xLTEvZmlndXJlLTAwMA.png?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9wcml2YXRlLXVzLWVhc3QtMS5tYW51c2Nkbi5jb20vc2Vzc2lvbkZpbGUvMkJTTnpzd0pqelNjR2NkbkdkcjNGTS9zYW5kYm94L2RjcTJ6d3RRWW5ydWV2eVJFRVpZOGctaW1hZ2VzXzE3OTExNjI0OTgyMDBfbmExZm5fTDJodmJXVXZkV0oxYm5SMUwzZHZjbXN2Y0dSemFTOXRZWEpyWkc5M2JpOWhjM05sZEhNdlJXNTBjbVZuWVY4MFgxOWZVRVJUU1Y4eExURXZabWxuZFhKbExUQXdNQS5wbmciLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3OTM0OTEyMDB9fX1dfQ__&Key-Pair-Id=K2QY5QTL8JSY6C&Signature=MEQCIC7FdDSlpSm0PAvmUKuOGfmAktCNTLE3xF~kupVCFhN2AiAe23EGLRDFXD4h4sHn3RbRT3oyBbollhfGTmTNUim2eA__)


```text

1    Introdução
O PriceBrother é um Produto Mínimo Viável (MVP) que coleta periodicamente preços de pro-
dutos em sites de comércio eletrônico, armazena o histórico dessas coletas, compara as variações
observadas e alerta o usuário quando identifica uma queda de preço relevante ou o atingimento
de um preço-alvo. Esta seção apresenta o diagrama de classes do sistema, elaborado a partir da
Especificação de Requisitos (segunda entrega) e dos casos de uso definidos na terceira entrega.
    O diagrama organiza o domínio em duas frentes complementares: (i) as entidades de negócio
persistidas, Usuario, Produto, Loja, Monitoramento, HistoricoPreco e Alerta, e (ii) os serviços
responsáveis por coleta, análise estatística e disparo de alertas, ColetaService, AnaliseService e
AlertaService, refletindo a separação de responsabilidades exigida pelo requisito não funcional
RNF07 (coleta, persistência, análise e apresentação mantidas independentes).


2    Diagrama de Classes
A Figura 1 apresenta o diagrama de classes da plataforma, elaborado no draw.io. O diagrama
indica, para cada classe, seus atributos e métodos com a respectiva visibilidade (+ público, -
privado), além dos relacionamentos de associação, agregação, composição e dependência entre as
classes, com as multiplicidades correspondentes.




                        Figure 1: Diagrama de classes do PriceBrother.



                                                2

```


---

## Página 3

```text

Principais relacionamentos representados no diagrama:

    • Usuario (1) – Monitoramento (0..*) e Produto (1) – Monitoramento (0..*):
      Monitoramento é uma classe associativa que representa o acompanhamento de um produto
      por um usuário, guardando o preço-alvo e se o alerta está ativo (RF04, RF14).

    • Loja (1) ◦– Produto (0..*): agregação, já que um produto pertence ao catálogo de
      uma loja, mas pode existir referência à loja independentemente da exclusão de um produto
      específico.

    • Produto (1) ♦– HistoricoPreco (0..*): composição, pois cada entrada de histórico
      pertence a exatamente um produto (RN04), sendo preservada mesmo quando o produto
      deixa de ser monitorado (RN05).

    • Usuario (1) – Alerta (0..*) e Produto (1) – Alerta (0..*): um alerta está sempre
      associado ao usuário que o recebe e ao produto que o originou.

    • ColetaService, AnaliseService e AlertaService: dependências («cria», «analisa»,
      «notifica») com as classes de domínio, refletindo que esses serviços operam sobre as
      entidades sem manterem estado persistente próprio de negócio.


3    Descrição das Classes
Para cada classe do diagrama, apresenta-se a seguir uma tabela com seus principais atributos,
métodos e uma breve descrição de seu papel no sistema.

                                       Classe Usuario
 Atributos     - id: UUID
               - nome: String
               - email: String
               - senhaHash: String
               - criadoEm: DateTime
 Métodos       + cadastrar(nome, email, senha): void
               + login(email, senha): boolean
               + logout(): void
               + alterarSenha(nova): void
 Descrição     Representa os usuários cadastrados na plataforma. Concentra os dados de au-
               tenticação e é o ponto de partida da associação com os produtos monitorados
               (via Monitoramento) e com os alertas recebidos.

                             Table 1: Descrição da classe Usuario




                                              3

```


---

## Página 4

```text

                                    Classe Produto
Atributos   - id: UUID
            - nome: String
            - urlProduto: String
            - ativo: boolean
            - criadoEm: DateTime
Métodos     + cadastrarProduto(nome, url, lojaId): void
            + removerProduto(): void
            + obterPrecoAtual(): float
Descrição   Representa um item de e-commerce cadastrado para monitoramento. Está as-
            sociada a uma Loja, a um ou mais registros de Monitoramento (um por usuário
            que o acompanha) e ao seu histórico de preços coletado ao longo do tempo.

                          Table 2: Descrição da classe Produto


                                      Classe Loja
Atributos   - id: UUID
            - nome: String
            - dominio: String
Métodos     + listarProdutos(): List<Produto>
Descrição   Representa o e-commerce onde um produto é vendido. Cada produto monitorado
            deve estar associado a exatamente uma loja identificada, conforme a Regra de
            Negócio RN03.

                            Table 3: Descrição da classe Loja


                                Classe Monitoramento
Atributos   - precoAlvo: float
            - alertaAtivo: boolean
            - dataCadastro: DateTime
Métodos     + ativarAlerta(): void
            + desativarAlerta(): void
            + definirPrecoAlvo(valor): void
Descrição   Classe associativa entre Usuario e Produto. Representa o acompanhamento de
            um produto específico por um usuário específico, guardando o preço-alvo definido
            (RF04) e se os alertas estão ativos para esse par usuário/produto (RF14).

                      Table 4: Descrição da classe Monitoramento




                                              4

```


---

## Página 5

```text

                                Classe HistoricoPreco
Atributos   - id: UUID
            - produtoId: UUID
            - preco: float
            - dataHoraColeta: DateTime
            - coletaValida: boolean
Métodos     + registrarColeta(preco, dataHora): void
            + obterMenorPreco(): float
            + calcularMediaHistorica(): float
Descrição   Representa uma entrada do histórico de preços de um produto, criada a cada
            execução válida do robô de scraping. É preservada mesmo quando o produto
            deixa de ser monitorado (RN05), permitindo consultas cronológicas e o cálculo
            de estatísticas (menor preço, média histórica).

                       Table 5: Descrição da classe HistoricoPreco


                                     Classe Alerta
Atributos   - id: UUID
            - produtoId: UUID
            - usuarioId: UUID
            - tipo: String
            - dataEnvio: DateTime
            - mensagem: String
Métodos     + disparar(): void
            + jaFoiEnviadoRecente(): boolean
Descrição   Representa uma notificação enviada a um usuário sobre um produto monitorado,
            seja por queda de preço relevante, seja por atingimento do preço-alvo. Controla
            o reenvio para evitar alertas repetidos para a mesma ocorrência (RN08).

                           Table 6: Descrição da classe Alerta


                           Classe ColetaService «service»
Atributos   - intervaloMinimo: int
            - maxTentativas: int
Métodos     + executarColeta(produto): HistoricoPreco
            + extrairPreco(url): float
            + registrarFalha(produto): void
Descrição   Serviço responsável pela camada de coleta (web scraping). Executa em inter-
            valos programados, respeita o intervalo mínimo entre requisições e o limite de
            tentativas (RNF08), criando novas entradas de HistoricoPreco ou registrando
            falhas sem apagar dados anteriores.

                       Table 7: Descrição da classe ColetaService




                                            5

```


---

## Página 6

```text

                             Classe AnaliseService «service»
 Atributos    - limiarQuedaPercentual: float
 Métodos      + compararComColetaAnterior(historico): float
              + compararComMedia(historico): float
              + identificarQuedaRelevante(historico): boolean
 Descrição    Serviço responsável pela camada de análise estatística, isolada da coleta e da ap-
              resentação (RNF07). Aplica os limiares definidos nas regras de negócio (RN06)
              para identificar quedas de preço relevantes a partir do histórico de um produto.

                         Table 8: Descrição da classe AnaliseService


                             Classe AlertaService «service»
 Atributos    - intervaloMinimoReenvio: int
 Métodos      + avaliarCondicoes(produto, analise): void
              + enviarEmail(alerta): void
 Descrição    Serviço responsável por decidir quando um alerta deve ser criado e por acionar
              o envio de e-mail ao usuário, respeitando as configurações de Monitoramento e
              o controle de reenvio (RN08, RN11).

                          Table 9: Descrição da classe AlertaService


4   Rastreabilidade com Casos de Uso
A Tabela 10 relaciona cada classe do diagrama com os casos de uso da terceira entrega em que
ela participa, mostrando como as decisões de modelagem de classes decorrem diretamente do
comportamento especificado nos casos de uso. “ ‘latex




                                               6

```


---

## Página 7

```text

Classe           Descrição                                                 Casos de Uso
                                                                           Relacionados
Usuario          Representa os usuários cadastrados, armazenando        UC01, UC02, UC03,
                 seus dados de autenticação e mantendo as               UC07, UC08, UC09,
                 associações com produtos monitorados e alertas               UC14
                 recebidos.
Produto          Representa o produto de e-commerce que será            UC04, UC05, UC06,
                 cadastrado, monitorado e consultado. Mantém            UC07, UC08, UC09,
                 associação com a loja, os monitoramentos e o           UC10, UC11, UC13,
                 histórico de preços.                                         UC14
Loja             Representa o e-commerce no qual o produto está         UC04, UC10, UC11
                 disponível, sendo utilizada para identificar a
                 origem dos preços coletados.
Monitoramento    Representa o vínculo entre um usuário e um             UC04, UC08, UC09,
                 produto, armazenando o preço-alvo e a                    UC13, UC14
                 configuração dos alertas para o produto
                 monitorado.
HistoricoPreco   Armazena os preços coletados ao longo do tempo         UC07, UC09, UC10,
                 para cada produto, permitindo consultas                      UC11
                 históricas e o cálculo de estatísticas utilizadas na
                 análise de variações de preço.
Alerta           Representa a notificação enviada ao usuário                UC13, UC14
                 quando ocorre uma condição de alerta, como
                 queda relevante de preço ou atingimento do
                 preço-alvo.
ColetaService    Responsável pela coleta dos preços nos sites de            UC10, UC12
                 comércio eletrônico, criando registros de histórico
                 a partir das coletas válidas e registrando falhas
                 quando necessário.
AnaliseService   Responsável pela análise das variações de preço,             UC11
                 utilizando o histórico para identificar quedas
                 relevantes de acordo com os limiares definidos
                 pelas regras de negócio.
AlertaService    Responsável por avaliar as condições para criação            UC13
                 de alertas e realizar o envio das notificações aos
                 usuários, respeitando as configurações de
                 monitoramento e as regras de reenvio.

                 Table 10: Rastreabilidade entre classes e casos de uso.

  “‘




                                             7

```
