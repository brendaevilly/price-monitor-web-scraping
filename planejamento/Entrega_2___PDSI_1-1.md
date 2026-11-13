# Entrega\_2\_\_\_PDSI\_1-1

## Página 1

```text

  Especificação de Requisitos: Plataforma para
            Monitoramento de Preços
  Ana Beatriz; Brenda Evilly, Jeslayne Julia e Karine Pimentel
                          August 2026


Sumário
1 Introdução                                                     2

2 Requisitos Funcionais (RF)                                     2

3 Requisitos Não Funcionais (RNF)                                3

4 Regras de Negócio                                               4

5 Priorização dos Requisitos                                     5

6 Critérios de Aceite                                            8

7 Considerações Finais                                           10




                               1

```


---

## Página 2

```text

1     Introdução
A aplicação proposta consiste em uma plataforma web para monitoramento
de preços em sites de comércio eletrônico. O sistema será desenvolvido como
um Produto Mínimo Viável (MVP), com escopo inicialmente limitado a um
nicho de produtos e a um número reduzido de lojas. Seu objetivo é coletar
preços de forma periódica, armazenar o histórico dessas informações, comparar
as variações observadas e avisar o usuário quando for identificada uma queda
considerada relevante.
    O problema central está na dificuldade de acompanhar manualmente as al-
terações de preço. Uma pessoa interessada em comprar determinado produto
normalmente observa apenas o valor exibido no momento da consulta, sem sa-
ber se ele está abaixo da média histórica ou se uma promoção representa, de
fato, uma boa oportunidade. A plataforma busca reduzir essa incerteza ao
transformar os dados coletados ao longo do tempo em informações acessíveis ao
consumidor.
    O sistema também poderá servir futuramente a afiliados, criadores de con-
teúdo e pequenos lojistas que precisam identificar rapidamente alterações de
preço. Entretanto, essas funcionalidades não fazem parte do núcleo obrigató-
rio desta versão. O MVP prioriza o fluxo principal scraping → histórico →
comparação → alerta, além do cadastro e da autenticação dos usuários.
    A especificação a seguir apresenta os requisitos funcionais, os requisitos não
funcionais, as regras de negócio, a priorização pelo método MoSCoW e os cri-
térios de aceite que serão utilizados para validar a implementação da aplicação.


2     Requisitos Funcionais (RF)
Os requisitos funcionais descrevem os serviços e comportamentos que a plata-
forma deve oferecer aos seus usuários ou executar internamente. Cada requisito
possui um identificador único e foi escrito de maneira objetiva e testável.

                        Tabela 1: Requisitos funcionais da aplicação

 ID           Descrição
 RF01         O sistema deve permitir o cadastro de usuários informando nome, e-mail e
              senha.
 RF02         O sistema deve permitir que usuários cadastrados realizem login utilizando
              e-mail e senha válidos.
 RF03         O sistema deve permitir que o usuário encerre sua sessão por meio da
              função de logout.
 RF04         O sistema deve permitir o cadastro de produtos para monitoramento,
              informando nome, URL da página do produto, loja e preço-alvo opcional.
 RF05         O sistema deve validar os dados mínimos de um produto monitorado antes
              de salvá-lo, incluindo URL válida e identificação da loja.



                                        2

```


---

## Página 3

```text

 ID          Descrição
 RF06        O sistema deve executar o robô de scraping em intervalos programados para
             coletar o preço e as informações básicas dos produtos cadastrados.
 RF07        O sistema deve armazenar cada coleta realizada com produto, loja, preço
             observado e data e hora da coleta.
 RF08        O sistema deve indicar quando uma coleta não puder ser realizada,
             registrando a falha sem apagar o histórico anterior do produto.
 RF09        O sistema deve permitir que o usuário consulte os produtos que estão sendo
             monitorados.
 RF10        O sistema deve exibir o histórico de preços de um produto em ordem
             cronológica.
 RF11        O sistema deve apresentar, para cada produto, o preço atual, o menor preço
             registrado e a média dos preços coletados, quando houver dados suficientes.
 RF12        O sistema deve comparar o preço atual com o preço da coleta anterior e
             com a média histórica do produto.
 RF13        O sistema deve identificar uma queda de preço relevante de acordo com os
             limiares definidos nas regras de negócio.
 RF14        O sistema deve permitir que o usuário ative ou desative o recebimento de
             alertas para cada produto monitorado.
 RF15        O sistema deve enviar um alerta por e-mail ao usuário quando for
             identificada uma queda de preço relevante ou quando o preço atingir o
             preço-alvo cadastrado.
 RF16        O sistema deve evitar o envio repetido de alertas para a mesma ocorrência
             de queda dentro de um intervalo definido.
 RF17        O sistema deve permitir que o usuário remova um produto de sua lista de
             monitoramento sem apagar, de forma indevida, os registros históricos já
             coletados.
 RF18        O sistema deve disponibilizar mensagens de erro compreensíveis quando
             uma operação não puder ser concluída.
 RF19        O sistema deve exibir uma tela de dashboard com consulta de produtos,
             histórico de preços em ordem cronológica, produtos e suas informações e
             alertas.


3     Requisitos Não Funcionais (RNF)
Os requisitos não funcionais estabelecem restrições e características de quali-
dade relacionadas ao desempenho, à segurança, à usabilidade, à manutenção e
à disponibilidade da aplicação.




                                      3

```


---

## Página 4

```text

                     Tabela 2: Requisitos não funcionais da aplicação

 ID           Descrição
 RNF01        As operações comuns da interface, como login, consulta de produtos e
              abertura do histórico, devem responder em até 2 segundos em condições
              normais de uso, desconsiderando o tempo de carregamento de páginas
              externas durante o scraping.
 RNF02        As senhas dos usuários não devem ser armazenadas em texto puro; devem
              ser protegidas por mecanismo de hash seguro disponibilizado pelo serviço
              de autenticação.
 RNF03        O acesso aos dados de monitoramento deve ser restrito ao usuário
              autenticado que cadastrou os respectivos produtos.
 RNF04        A aplicação deve utilizar comunicação HTTPS sempre que estiver
              publicada em ambiente de produção.
 RNF05        A interface deve ser responsiva e funcionar adequadamente em
              computadores, tablets e dispositivos móveis.
 RNF06        A aplicação deve apresentar mensagens de validação e erro em português,
              de forma clara para o usuário.
 RNF07        O sistema deve manter separadas as responsabilidades de coleta,
              persistência, análise e apresentação, permitindo a manutenção
              independente dos componentes.
 RNF08        O robô de scraping deve respeitar um intervalo mínimo entre requisições e
              não deve realizar tentativas ilimitadas em caso de erro.
 RNF09        O sistema deve registrar logs técnicos suficientes para identificar falhas de
              autenticação, coleta, persistência e envio de alertas, sem expor senhas ou
              tokens.
 RNF10        A aplicação deve ser executável utilizando prioritariamente serviços e
              bibliotecas disponíveis em camadas gratuitas, conforme as restrições
              orçamentárias do projeto.
 RNF11        O código-fonte deve ser versionado no GitHub e as alterações devem passar
              por revisão via Pull Request antes de serem incorporadas à branch
              principal.
 RNF12        As funcionalidades implementadas devem possuir testes manuais
              documentados e, quando aplicável, testes automatizados para os fluxos
              críticos.


4     Regras de Negócio
As regras de negócio representam as condições específicas do domínio de monito-
ramento de preços que devem ser respeitadas independentemente da tecnologia
utilizada na implementação.




                                      4

```


---

## Página 5

```text

                          Tabela 3: Regras de negócio da aplicação

 ID           Descrição
 RN01         Um usuário deve possuir um e-mail único no sistema e não pode realizar
              mais de um cadastro utilizando o mesmo endereço.
 RN02         Somente usuários autenticados podem cadastrar, consultar, alterar ou
              remover produtos de sua própria lista de monitoramento.
 RN03         Um produto monitorado deve possuir uma URL pública de uma página de
              produto e uma loja identificada.
 RN04         Cada coleta válida deve registrar o preço observado e o instante em que a
              coleta ocorreu, formando uma nova entrada no histórico.
 RN05         O histórico de preços é preservado mesmo quando o produto deixa de ser
              monitorado, salvo em caso de exclusão definitiva prevista na implementação.
 RN06         Uma queda será considerada relevante quando o preço atual for pelo menos
              10% menor que o preço da coleta anterior ou pelo menos 10% menor que a
              média histórica, desde que exista quantidade mínima de dados para a
              comparação.
 RN07         Quando o usuário informar um preço-alvo, o alerta deverá ser disparado
              quando o preço atual for menor ou igual ao valor definido.
 RN08         O sistema não deve enviar mais de um alerta para a mesma ocorrência de
              preço sem que ocorra uma nova variação relevante ou que o preço volte a
              um patamar superior ao limiar configurado.
 RN09         Uma coleta que não encontrar preço válido não deve gerar registro de preço
              igual a zero nem ser interpretada como queda.
 RN10         A análise estatística deve utilizar somente dados válidos associados ao
              mesmo produto, não misturando históricos de produtos diferentes.
 RN11         Os alertas devem ser enviados apenas quando o usuário tiver habilitado essa
              opção para o produto monitorado e possuir um endereço de e-mail válido.
 RN12         O sistema atua somente como observador e informante: não altera preços,
              não realiza compras e não executa ações de negociação nos sites
              monitorados.
 RN13         A coleta deve ser limitada aos dados públicos necessários ao monitoramento,
              sem armazenar dados pessoais encontrados nas páginas das lojas.
 RN14         Caso a estrutura da página de uma loja seja alterada ou a coleta falhe, o
              sistema deve preservar os dados anteriores e registrar a ocorrência para
              posterior manutenção.


5     Priorização dos Requisitos
A priorização foi realizada utilizando a técnica MoSCoW. Os requisitos classifi-
cados como Must compõem o núcleo mínimo necessário para demonstrar o fluxo
principal da plataforma. Os requisitos Should são importantes para a qualidade
da experiência, mas podem ser concluídos depois da estabilização do núcleo.
Os requisitos Could representam melhorias desejáveis e os requisitos Won’t não


                                       5

```


---

## Página 6

```text

serão implementados nesta versão do projeto.




                                     6

```


---

## Página 7

```text

         Tabela 4: Priorização dos requisitos pelo método MoSCoW
Requisito     Descrição resumida                                   Prioridade

RF01          Cadastro de usuário                                    Must
RF02          Login de usuário                                       Must
RF03          Encerramento da sessão                                 Should
RF04–         Cadastro e validação de produtos                       Must
RF05
RF06–         Coleta periódica e persistência do histórico           Must
RF08
RF09–         Consulta e visualização do histórico                   Should
RF11
RF12–         Comparação e identificação de quedas                   Must
RF13
RF14–         Configuração e envio de alertas                        Must
RF16
RF17          Remoção de produto monitorado                          Should
RF18          Mensagens de erro compreensíveis                       Should
RNF01         Desempenho das operações comuns                        Should
RNF02–        Segurança de credenciais, dados e comunicação          Must
RNF04
RNF05–        Responsividade e clareza da interface                  Should
RNF06
RNF07–        Manutenibilidade, limites de coleta e logs             Must
RNF09
RNF10         Uso prioritário de camadas gratuitas                   Must
RNF11–        Versionamento, revisão e testes                        Must
RNF12
RN01–         Regras de negócio do domínio                           Must
RN14

RF19          Notificações via push além do e-mail                   Could
RF20          Ampliação do monitoramento para vários nichos e        Could
              grande quantidade de lojas
RF21          Geração automática de links de afiliado                Could
RF22          Dashboard de cliques, conversões e receita para        Won’t
              afiliados
RF23          Aplicativo mobile nativo                               Won’t
RF24          Precificação automática ou negociação com lojas        Won’t
RF25          Camada de análise via RAG ou modelo de linguagem       Won’t


                                     7

```


---

## Página 8

```text

   Os requisitos RF19 a RF25 foram registrados como funcionalidades futuras
ou explicitamente fora do escopo desta versão. A decisão mantém o foco no
MVP e reduz o risco de comprometer o fluxo essencial por causa de integrações
externas, funcionalidades comerciais ou componentes que exigiriam infraestru-
tura adicional.


6     Critérios de Aceite
Os critérios de aceite definem condições objetivas para verificar se cada requi-
sito foi implementado corretamente. A funcionalidade será considerada aceita
quando o resultado observado atender ao critério correspondente, sem interrom-
per o fluxo principal da aplicação.

                   Tabela 5: Critérios de aceite dos requisitos funcionais

 ID            Critério de aceite
 RF01          Será aceito quando um novo usuário conseguir criar uma conta com nome
               preenchido, e-mail válido e senha conforme a política definida, recebendo
               confirmação visual de sucesso. O sistema deve rejeitar e-mails inválidos ou
               já cadastrados.
 RF02          Será aceito quando um usuário cadastrado conseguir acessar a aplicação
               com credenciais válidas e quando credenciais inválidas forem recusadas
               com mensagem adequada.
 RF03          Será aceito quando o usuário selecionar logout e deixar de acessar as
               páginas protegidas sem realizar novo login.
 RF04–         Serão aceitos quando o usuário conseguir cadastrar um produto com
 RF05          nome, URL válida, loja e preço-alvo opcional, e quando o sistema impedir
               o salvamento de dados obrigatórios ausentes ou inválidos.
 RF06–         Serão aceitos quando uma execução programada acessar a página
 RF08          configurada, extrair preço válido, salvar a coleta com data e hora e
               registrar uma falha sem criar preço incorreto quando a extração não for
               possível.
 RF09–         Serão aceitos quando o usuário autenticado visualizar sua lista de
 RF11          produtos e, ao selecionar um item, consultar os preços coletados em ordem
               cronológica, com preço atual, menor preço e média histórica quando
               aplicável.
 RF12–         Serão aceitos quando o sistema calcular a variação em relação à coleta
 RF13          anterior e à média histórica, classificando corretamente uma queda que
               atenda ao limiar de 10% e não classificando como relevante uma variação
               abaixo desse limiar.
 RF14–         Serão aceitos quando o usuário conseguir habilitar ou desabilitar alertas e
 RF16          receber, uma única vez por ocorrência, um e-mail contendo o produto, a
               loja, o preço atual e o motivo do alerta.




                                       8

```


---

## Página 9

```text

ID         Critério de aceite
RF17       Será aceito quando o usuário conseguir remover um produto de sua lista
           de monitoramento e o sistema deixar de realizar novas coletas para esse
           item, preservando os registros históricos conforme a política definida.
RF18       Será aceito quando erros de validação, autenticação, coleta ou envio de
           alertas apresentarem mensagens compreensíveis, sem expor detalhes
           técnicos sensíveis.


         Tabela 6: Critérios de aceite dos requisitos não funcionais e regras
         de negócio

ID         Critério de aceite
RNF01      Será aceito quando testes manuais ou automatizados demonstrarem que as
           operações comuns especificadas respondem em até 2 segundos em
           condições normais, excluindo atrasos de páginas externas.
RNF02–     Serão aceitos quando não houver senhas em texto puro no banco, quando
RNF04      usuários não acessarem dados de outras contas e quando a aplicação
           publicada utilizar HTTPS.
RNF05–     Serão aceitos quando as telas principais forem utilizáveis em resoluções de
RNF06      computador e celular e apresentarem textos de interface e erro em
           português.
RNF07–     Serão aceitos quando os componentes estiverem organizados conforme suas
RNF09      responsabilidades, o coletor respeitar limites de requisição e os logs
           permitirem identificar falhas sem registrar segredos.
RNF10–     Serão aceitos quando o sistema puder ser executado dentro do orçamento
RNF12      previsto, o código estiver versionado com revisão por Pull Request e os
           fluxos críticos possuírem evidência de teste.
RN01–      Serão aceitos quando o sistema impedir e-mails duplicados, bloquear o
RN03       acesso de usuários não autenticados e rejeitar produtos sem URL válida ou
           loja identificada.
RN04–      Serão aceitos quando cada coleta válida gerar uma entrada com preço e
RN05       data e hora e quando o histórico não for apagado por uma falha de coleta
           ou pela remoção do monitoramento.
RN06–      Serão aceitos quando os limiares de queda, preço-alvo e controle de
RN08       repetição de alertas produzirem o comportamento definido nos testes com
           valores conhecidos.
RN09–      Serão aceitos quando coletas sem preço não gerarem valor zero, produtos
RN11       distintos não compartilharem estatísticas e alertas não forem enviados com
           a opção desativada.
RN12–      Serão aceitos quando a plataforma não alterar páginas externas, coletar
RN14       apenas dados públicos necessários e preservar o histórico diante de falhas
           causadas por mudanças na estrutura das lojas.



                                   9

```


---

## Página 10

```text

7    Considerações Finais
A especificação define um conjunto de requisitos compatível com o escopo acadê-
mico do projeto e com o cronograma estabelecido na primeira entrega. O núcleo
obrigatório é formado pelo cadastro e autenticação, pelo cadastro de produtos,
pela coleta periódica, pelo armazenamento do histórico, pela comparação de
preços e pelo envio de alertas.
    A priorização evita que funcionalidades futuras, como notificações push, inte-
gração com plataformas de afiliados, aplicativo mobile nativo ou análise baseada
em RAG, comprometam a entrega do fluxo principal. Dessa forma, a equipe po-
derá validar primeiro uma versão funcional de ponta a ponta e, posteriormente,
evoluir a plataforma de acordo com o tempo disponível e o retorno obtido nas
apresentações da disciplina.
    Os critérios de aceite apresentados neste documento deverão orientar os tes-
tes realizados pela equipe em cada ciclo de desenvolvimento. Uma funcionali-
dade somente será considerada concluída quando atender ao requisito corres-
pondente, respeitar as regras de negócio e não interromper o fluxo principal do
sistema.




                                       10

```
