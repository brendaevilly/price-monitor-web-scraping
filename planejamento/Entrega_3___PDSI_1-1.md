# Entrega\_3\_\_\_PDSI\_1-1

## Página 1

```text

                      Casos de Uso: PriceBrother
      Ana Beatriz      Brenda Evilly       Jeslayne Julia   Karine Pimentel

                                 September 2026


Sumário

1 Introdução                                                                   2

2 Identificação dos Atores                                                     2

3 Diagrama de Casos de Uso (UML)                                               2

4 Descrição dos Casos de Uso                                                   4

5 Rastreabilidade com os Requisitos                                           10




                                       1

```


---

## Página 2

```text

1    Introdução
O PriceBrother, "Grande irmão dos preços", tem como objetivo acompanhar, de forma autom-
atizada, as variações de preço de produtos em sites de comércio eletrônico, construindo um
histórico que permite identificar quedas relevantes e notificar o usuário no momento oportuno.
Esta seção apresenta a modelagem dos casos de uso do sistema, elaborada a partir da Especifi-
cação de Requisitos (segunda entrega) e do documento de contexto e escopo do projeto (primeira
entrega).
    Os casos de uso são utilizados aqui como ferramenta de modelagem para descrever, de maneira
estruturada, como cada ator interage com o sistema: o usuário final, que cadastra produtos e con-
sulta o histórico de preços; o robô de scraping, que executa a coleta periódica de forma autônoma;
e o serviço de e-mail, responsável por efetivamente entregar os alertas. Essa modelagem serve de
base para as próximas entregas do projeto, em especial o diagrama de classes (quarta entrega) e
a implementação do fluxo principal scraping → histórico → comparação → alerta.


2    Identificação dos Atores
Foram identificados três atores que interagem com o sistema, conforme planejado na fase de
levantamento dos casos de uso (Fase 3 do cronograma, primeira entrega):

    • Usuário: Pessoa que deseja acompanhar o preço de produtos específicos. É o ator primário
      do sistema: cadastra-se, realiza login, cadastra e remove produtos monitorados, consulta o
      histórico de preços, configura alertas e recebe as notificações de queda de preço.

    • Robô de Scraping: Ator automatizado, executado em intervalos programados pelo
      próprio sistema (via APScheduler), responsável por coletar os preços dos produtos cadastra-
      dos, registrar o histórico e identificar falhas de coleta.

    • Serviço de E-mail: Sistema externo (camada de e-mail transacional) acionado pela
      plataforma para efetivamente entregar o alerta de queda de preço ao usuário.


3    Diagrama de Casos de Uso (UML)
A Figura 1 apresenta o diagrama de casos de uso da plataforma, elaborado no draw.io. O dia-
grama mostra os três atores identificados, os catorze casos de uso do sistema e os relacionamentos
de inclusão («include») e extensão («extend») entre casos relacionados, por exemplo, o caso
de uso Visualizar Dashboard inclui Consultar Produtos Monitorados e Consultar Histórico de
Preços, enquanto Disparar Alerta de Preço estende Comparar Preços e Identificar Queda, sendo
executado apenas quando uma variação relevante é identificada.




                                                2

```


---

## Página 3
![Figura da página 3](https://private-us-east-1.manuscdn.com/sessionFile/2BSNzswJjzScGcdnGdr3FM/sandbox/dcq2zwtQYnruevyREEZY8g-images_1791162498220_na1fn_L2hvbWUvdWJ1bnR1L3dvcmsvcGRzaS9tYXJrZG93bi9hc3NldHMvRW50cmVnYV8zX19fUERTSV8xLTEvZmlndXJlLTAwMA.png?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9wcml2YXRlLXVzLWVhc3QtMS5tYW51c2Nkbi5jb20vc2Vzc2lvbkZpbGUvMkJTTnpzd0pqelNjR2NkbkdkcjNGTS9zYW5kYm94L2RjcTJ6d3RRWW5ydWV2eVJFRVpZOGctaW1hZ2VzXzE3OTExNjI0OTgyMjBfbmExZm5fTDJodmJXVXZkV0oxYm5SMUwzZHZjbXN2Y0dSemFTOXRZWEpyWkc5M2JpOWhjM05sZEhNdlJXNTBjbVZuWVY4elgxOWZVRVJUU1Y4eExURXZabWxuZFhKbExUQXdNQS5wbmciLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3OTM0OTEyMDB9fX1dfQ__&Key-Pair-Id=K2QY5QTL8JSY6C&Signature=MEUCIQDRwWaNNba4DHPEWX6CjqtljzsvUd7B6wfVUrurI6HQGQIgaGnID~qGqeA2e3ifEWTWt-tFouUWD-vjkhIWE2jfSpw_)


```text

Figure 1: Diagrama de casos de uso do ator usuário no PriceBrother.




                                3

```


---

## Página 4
![Figura da página 4](https://private-us-east-1.manuscdn.com/sessionFile/2BSNzswJjzScGcdnGdr3FM/sandbox/dcq2zwtQYnruevyREEZY8g-images_1791162498220_na1fn_L2hvbWUvdWJ1bnR1L3dvcmsvcGRzaS9tYXJrZG93bi9hc3NldHMvRW50cmVnYV8zX19fUERTSV8xLTEvZmlndXJlLTAwMg.png?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9wcml2YXRlLXVzLWVhc3QtMS5tYW51c2Nkbi5jb20vc2Vzc2lvbkZpbGUvMkJTTnpzd0pqelNjR2NkbkdkcjNGTS9zYW5kYm94L2RjcTJ6d3RRWW5ydWV2eVJFRVpZOGctaW1hZ2VzXzE3OTExNjI0OTgyMjBfbmExZm5fTDJodmJXVXZkV0oxYm5SMUwzZHZjbXN2Y0dSemFTOXRZWEpyWkc5M2JpOWhjM05sZEhNdlJXNTBjbVZuWVY4elgxOWZVRVJUU1Y4eExURXZabWxuZFhKbExUQXdNZy5wbmciLCJDb25kaXRpb24iOnsiRGF0ZUxlc3NUaGFuIjp7IkFXUzpFcG9jaFRpbWUiOjE3OTM0OTEyMDB9fX1dfQ__&Key-Pair-Id=K2QY5QTL8JSY6C&Signature=MEQCIEF0mBK7pwUjdAIXoOG0t92Szm~DMhKyeBP227RvPiWYAiAZNWTa6Il2XAywmC0cOzPLXbjPF8o-7jCF~HxGZThd6Q__)


```text

       Figure 2: Diagrama de casos de uso dos atores scraping e e-mail no PriceBrother.


4    Descrição dos Casos de Uso
Para cada caso de uso identificado no diagrama, apresenta-se a seguir uma ficha detalhada
contendo identificador, nome, ator principal, pré-condições, fluxo principal, fluxos alternativos e
pós-condições, seguindo o modelo definido para esta entrega.

 Identificador             UC01
 Nome                      Cadastrar Usuário
 Ator Principal            Usuário
 Pré-condições             Usuário ainda não possui cadastro na plataforma.
 Fluxo Principal
                           1. Usuário acessa a tela de cadastro.
                           2. Usuário informa nome, e-mail e senha.
                           3. Sistema valida o formato do e-mail e a política de senha.
                           4. Sistema verifica se o e-mail já está cadastrado.
                           5. Sistema cria a conta e exibe confirmação de sucesso.
 Fluxos Alternativos       • 3a. Se o e-mail já estiver cadastrado, o sistema exibe mensagem
                             de erro e não cria a conta.
                           • 3b. Se os dados obrigatórios estiverem ausentes ou inválidos, o
                             sistema solicita a correção antes de prosseguir.
 Pós-condições             Usuário cadastrado no sistema e apto a realizar login.

                   Table 1: Ficha do caso de uso UC01 – Cadastrar Usuário




                                                4

```


---

## Página 5

```text

Identificador          UC02
Nome                   Realizar Login
Ator Principal         Usuário
Pré-condições          Usuário deve possuir cadastro válido.
Fluxo Principal
                       1. Usuário informa e-mail e senha.
                       2. Sistema valida as credenciais.
                       3. Sistema concede acesso à área restrita.
Fluxos Alternativos    • 2a. Se a senha ou o e-mail estiverem incorretos, o sistema exibe
                         mensagem de erro e mantém o usuário na tela de login.
Pós-condições          Usuário autenticado ou informado sobre erro.

                  Table 2: Ficha do caso de uso UC02 – Realizar Login


Identificador          UC03
Nome                   Encerrar Sessão
Ator Principal         Usuário
Pré-condições          Usuário deve estar autenticado no sistema.
Fluxo Principal
                       1. Usuário seleciona a opção de logout.
                       2. Sistema encerra a sessão ativa do usuário.
                       3. Sistema redireciona o usuário para a tela de login.
Fluxos Alternativos    • Não se aplica.
Pós-condições          Sessão encerrada; usuário deixa de acessar páginas protegidas sem
                       novo login.

                  Table 3: Ficha do caso de uso UC03 – Encerrar Sessão


Identificador          UC04
Nome                   Cadastrar Produto Monitorado
Ator Principal         Usuário
Pré-condições          Usuário deve estar autenticado.
Fluxo Principal
                       1. Usuário acessa a opção de cadastrar produto.
                       2. Usuário informa nome, URL da página do produto, loja e, op-
                          cionalmente, um preço-alvo.
                       3. Sistema valida a URL informada e a identificação da loja.
                       4. Sistema salva o produto na lista de monitoramento do usuário.
Fluxos Alternativos    • 3a. Se a URL for inválida ou a loja não puder ser identificada, o
                         sistema rejeita o cadastro e exibe mensagem de erro.
Pós-condições          Produto adicionado à lista de monitoramento do usuário, apto a
                       receber coletas periódicas.

          Table 4: Ficha do caso de uso UC04 – Cadastrar Produto Monitorado



                                            5

```


---

## Página 6

```text

Identificador         UC05
Nome                  Remover Produto Monitorado
Ator Principal        Usuário
Pré-condições         Usuário autenticado deve possuir ao menos um produto monitorado.
Fluxo Principal
                      1. Usuário seleciona um produto em sua lista de monitoramento.
                      2. Usuário confirma a remoção do produto.
                      3. Sistema interrompe novas coletas para o produto.
                      4. Sistema preserva os registros históricos já coletados.
Fluxos Alternativos   • Não se aplica.
Pós-condições         Produto removido da lista de monitoramento do usuário, sem perda
                      do histórico já coletado.

          Table 5: Ficha do caso de uso UC05 – Remover Produto Monitorado


Identificador         UC06
Nome                  Consultar Produtos Monitorados
Ator Principal        Usuário
Pré-condições         Usuário deve estar autenticado.
Fluxo Principal
                      1. Usuário acessa a lista de produtos monitorados.
                      2. Sistema exibe os produtos cadastrados pelo usuário autenticado.
Fluxos Alternativos   • Não se aplica.
Pós-condições         Usuário visualiza os produtos que monitora.

         Table 6: Ficha do caso de uso UC06 – Consultar Produtos Monitorados


Identificador         UC07
Nome                  Consultar Histórico de Preços
Ator Principal        Usuário
Pré-condições         Usuário deve estar autenticado e ter selecionado um produto moni-
                      torado.
Fluxo Principal
                      1. Usuário seleciona um produto monitorado.
                      2. Sistema exibe o histórico de preços em ordem cronológica.
                      3. Sistema apresenta o preço atual, o menor preço registrado e a
                         média histórica dos preços coletados, quando houver dados sufi-
                         cientes.
Fluxos Alternativos   • 3a. Se não houver dados suficientes para calcular a média histórica,
                        o sistema informa essa limitação ao usuário e não classifica a vari-
                        ação de preço por faixa de queda.
Pós-condições         Usuário visualiza o histórico e as estatísticas de preço do produto
                      selecionado.

          Table 7: Ficha do caso de uso UC07 – Consultar Histórico de Preços


                                           6

```


---

## Página 7

```text

Identificador           UC08
Nome                    Configurar Alertas do Produto
Ator Principal          Usuário
Pré-condições           Usuário autenticado deve possuir o produto em sua lista de moni-
                        toramento.
Fluxo Principal
                        1. Usuário seleciona um produto monitorado.
                        2. Usuário ativa ou desativa o recebimento de alertas para esse pro-
                           duto.
                        3. Sistema salva a configuração de alerta.
Fluxos Alternativos     • Não se aplica.
Pós-condições           Configuração de alerta do produto atualizada conforme escolha do
                        usuário.

          Table 8: Ficha do caso de uso UC08 – Configurar Alertas do Produto


Identificador           UC09
Nome                    Visualizar Dashboard
Ator Principal          Usuário
Pré-condições           Usuário deve estar autenticado.
Fluxo Principal
                        1. Usuário acessa a tela de dashboard.
                        2. Sistema inclui a consulta de produtos monitorados (UC06).
                        3. Sistema inclui a consulta de histórico de preços em ordem
                           cronológica (UC07).
                        4. Sistema apresenta, em uma única tela, os produtos, suas infor-
                           mações e os alertas configurados.
Fluxos Alternativos     • Não se aplica.
Pós-condições           Usuário visualiza, de forma consolidada, produtos, histórico e alertas.

                Table 9: Ficha do caso de uso UC09 – Visualizar Dashboard




                                             7

```


---

## Página 8

```text

Identificador          UC10
Nome                   Coletar Preços
Ator Principal         Robô de Scraping
Pré-condições          Deve existir ao menos um produto cadastrado para monitoramento.
Fluxo Principal
                       1. Robô de scraping é acionado em intervalo programado.
                       2. Robô acessa a página do produto cadastrado.
                       3. Robô extrai o preço e as informações básicas do produto.
                       4. Sistema registra a coleta com produto, loja, preço observado e
                          data e hora.
                       5. Sistema inclui a comparação do preço coletado com o histórico do
                          produto (UC11).
Fluxos Alternativos    • 3a. Se a extração falhar, o sistema estende o fluxo para o caso
                         de uso Registrar Falha de Coleta (UC12), preservando o histórico
                         anterior.
Pós-condições          Nova entrada de histórico registrada para o produto, ou falha reg-
                       istrada sem perda de dados anteriores.

                  Table 10: Ficha do caso de uso UC10 – Coletar Preços


Identificador          UC11
Nome                   Comparar Preços e Identificar Queda
Ator Principal         Robô de Scraping
Pré-condições          Deve existir uma coleta de preço recém-realizada para o produto.
Fluxo Principal
                       1. Sistema recupera o preço atual e os registros históricos do pro-
                          duto.
                       2. Sistema calcula a média histórica dos preços coletados para o
                          produto.
                       3. Sistema calcula a variação percentual entre o preço atual e a média
                          histórica, utilizando a média como preço de referência.
                       4. Sistema classifica a queda de preço conforme as regras de negócio:
                             • Pequena queda: redução entre 5% e 9%;
                             • Queda relevante: redução entre 10% e 19%;
                             • Grande queda: redução igual ou superior a 20%.
                       5. Sistema registra o resultado da análise e a classificação da queda
                          para o produto.
Fluxos Alternativos    • 3a. Se não houver dados históricos suficientes para calcular a
                         média, o sistema não classifica a variação como queda.
                       • 4a. Se a redução for inferior a 5%, o sistema registra a variação,
                         mas não a classifica como queda para fins de alerta.
Pós-condições          Produto classificado conforme a faixa de redução de preço identifi-
                       cada ou registrado sem queda relevante quando a redução for inferior
                       a 5%.

       Table 11: Ficha do caso de uso UC11 – Comparar Preços e Identificar Queda



                                            8

```


---

## Página 9

```text

Identificador          UC12
Nome                   Registrar Falha de Coleta
Ator Principal         Robô de Scraping
Pré-condições          Uma tentativa de coleta para um produto monitorado deve estar em
                       andamento.
Fluxo Principal
                       1. Robô de scraping tenta acessar a página do produto e não con-
                          segue extrair um preço válido.
                       2. Sistema registra a ocorrência de falha, sem apagar o histórico
                          anterior do produto.
                       3. Sistema não gera registro de preço igual a zero nem interpreta a
                          falha como queda de preço.
Fluxos Alternativos    • Não se aplica.
Pós-condições          Falha registrada para posterior manutenção, com o histórico anterior
                       do produto preservado.

            Table 12: Ficha do caso de uso UC12 – Registrar Falha de Coleta


Identificador          UC13
Nome                   Disparar Alerta de Preço
Ator Principal         Serviço de E-mail
Pré-condições          O produto deve ter alertas ativados pelo usuário e possuir e-mail
                       válido associado.
Fluxo Principal
                       1. Sistema estende o caso de uso Comparar Preços e Identificar
                          Queda (UC11) quando é identificada uma queda de preço a par-
                          tir de 5% em relação à média histórica ou quando o preço-alvo
                          definido pelo usuário é atingido.
                       2. Sistema verifica se já foi enviado um alerta para a mesma ocor-
                          rência dentro do intervalo definido.
                       3. Sistema aciona o serviço de e-mail para o envio do alerta ao
                          usuário.
                       4. Serviço de e-mail entrega a mensagem contendo produto, loja,
                          preço atual e o motivo do alerta.
Fluxos Alternativos    • 2a. Se já houver um alerta recente para a mesma ocorrência, o
                         sistema não envia um novo alerta repetido.
Pós-condições          Usuário notificado por e-mail sobre a queda de preço ou o atingi-
                       mento do preço-alvo.

            Table 13: Ficha do caso de uso UC13 – Disparar Alerta de Preço




                                           9

```


---

## Página 10

```text

 Identificador             UC14
 Nome                      Receber Alerta de Preço
 Ator Principal            Usuário
 Pré-condições             Um alerta deve ter sido disparado para o usuário (UC13).
 Fluxo Principal
                           1. Usuário recebe o e-mail de alerta de queda de preço ou de ating-
                              imento do preço-alvo.
                           2. Usuário acessa a plataforma a partir do alerta recebido.
                           3. Sistema inclui a consulta do histórico de preços do produto
                              (UC07), permitindo ao usuário avaliar a oportunidade.
 Fluxos Alternativos       • Não se aplica.
 Pós-condições             Usuário informado sobre a oportunidade e com acesso ao histórico
                           do produto para decisão.

               Table 14: Ficha do caso de uso UC14 – Receber Alerta de Preço


5    Rastreabilidade com os Requisitos
A Tabela 15 relaciona cada caso de uso identificado com os requisitos funcionais (RF) definidos na
Especificação de Requisitos (segunda entrega), permitindo verificar que todo requisito funcional
relevante ao MVP está coberto por ao menos um caso de uso.

 Caso de Uso      Descrição                                         Requisitos Relacionados
 UC01             Cadastrar Usuário                                 RF01
 UC02             Realizar Login                                    RF02
 UC03             Encerrar Sessão                                   RF03
 UC04             Cadastrar Produto Monitorado                      RF04, RF05
 UC05             Remover Produto Monitorado                        RF17
 UC06             Consultar Produtos Monitorados                    RF09
 UC07             Consultar Histórico de Preços                     RF10, RF11
 UC08             Configurar Alertas do Produto                     RF14
 UC09             Visualizar Dashboard                              RF19
 UC10             Coletar Preços                                    RF06, RF07
 UC11             Comparar Preços e Identificar Queda               RF12, RF13
 UC12             Registrar Falha de Coleta                         RF08
 UC13             Disparar Alerta de Preço                          RF15, RF16
 UC14             Receber Alerta de Preço                           RF15

              Table 15: Rastreabilidade entre casos de uso e requisitos funcionais.




                                               10

```
