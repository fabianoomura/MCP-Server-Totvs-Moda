# TOTVS Moda MCP Server

> IA aplicada ao TOTVS Moda: uma camada MCP para diminuir a distância entre uma pergunta e uma resposta.

[![PyPI version](https://img.shields.io/pypi/v/totvs-moda-mcp)](https://pypi.org/project/totvs-moda-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/totvs-moda-mcp)](https://pypi.org/project/totvs-moda-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Servidor **MCP (Model Context Protocol)** para a **API V2 do TOTVS Moda**, criado para permitir que assistentes de IA consultem e operem o ERP por meio de ferramentas padronizadas.

> **Projeto independente e não oficial.**
> Não possui vínculo com a TOTVS S.A.
> Construído com foco em uso real da API, automação de rotinas e apoio ao desenvolvimento de integrações.

---

## Por que este projeto existe?

Este projeto nasceu de uma necessidade prática.

Participei da implantação do TOTVS Moda em uma operação que vinha de um ERP mais simples. O TOTVS Moda trouxe muito mais robustez, módulos completos, APIs REST, recursos como o **DICFM001** para criação de consultas e relatórios personalizados, além de uma base de informações muito rica.

O desafio nunca foi a falta de dados.

O desafio era transformar uma pergunta em uma resposta.

Muitas vezes, encontrar uma informação significava navegar por várias telas, montar filtros, criar relatórios específicos, consultar a documentação da API ou desenvolver uma integração.

No início, escrevi pequenos scripts em Python para facilitar minha própria rotina.

Com o tempo, esses scripts evoluíram para automações, APIs, integrações e ferramentas internas.

Anos depois, estudando Inteligência Artificial e MCP, percebi que aqueles scripts poderiam evoluir para algo maior: uma camada capaz de transformar funcionalidades da API do TOTVS Moda em ferramentas que um modelo de IA consegue compreender e utilizar.

O objetivo não é substituir o ERP, relatórios ou BI.

O objetivo é aproximar pessoas, desenvolvedores e sistemas do conhecimento que já existe dentro do TOTVS Moda.

---

## O que é

O **Model Context Protocol (MCP)** é um protocolo aberto que permite que modelos de linguagem, como Claude, Copilot, Cursor, VS Code Agent e outros clientes compatíveis, utilizem ferramentas externas de forma padronizada.

Este projeto expõe a **API V2 do TOTVS Moda** como um conjunto de tools MCP.

Na prática, isso permite consultar informações do ERP, compor respostas, acelerar integrações e apoiar o desenvolvimento de sistemas usando linguagem natural.

---

## Exemplos de uso

Exemplos reais do que pode ser feito:

```text
"Quanto vendemos hoje por canal?"
"Quais pedidos foram criados hoje na filial 1?"
"Qual o faturamento da semana passada por filial?"
"Me mostra os 10 clientes que mais compraram este mês"
"Resumo do dia: vendas, contas a receber e contas a pagar"
"Dados completos do produto 13180"
"Dados da NF 143218"
"Dados do pedido 120040"
"Quais produtos estão com pronta entrega?"
"Visão 360 do cliente CPF 123.456.789-00"
"Qual o preço de venda e custo do produto 10000?"
"Ficha de consumo do produto 13020"
"Quais títulos vencem até sexta no contas a receber?"
"O que tenho para pagar esta semana?"
"Como obtenho essas informações pela API?"
"Me mostra os padrões de uso do sistema nos últimos 30 dias"
```

---

## Para quem este projeto pode ajudar?

Este projeto pode ser útil para:

* desenvolvedores que trabalham com TOTVS Moda;
* equipes que precisam consumir a API V2 com mais agilidade;
* empresas que ainda não possuem um BI confiável ou atualizado;
* operações que dependem de consultas recorrentes ao ERP;
* times que desejam criar agentes de IA conectados ao ERP;
* pessoas que querem reduzir tarefas repetitivas e acelerar análises operacionais.

Um BI bem estruturado responde muitas perguntas com velocidade.

Mas nem toda empresa possui um BI maduro. E, mesmo quando possui, normalmente ele responde às perguntas que alguém já modelou.

O ERP guarda muito mais conhecimento do que normalmente chega aos dashboards.

Este projeto tenta reduzir essa distância.

---

## Cobertura

**213 tools** organizadas em 21 módulos da API V2:

* Harness de endpoints: `251/251` caminhos mapeados na matriz derivada
* Núcleo não-Analytics: `190/190`
* Analytics/painéis: `61/61` via gateway opcional, desabilitado por padrão
* Suite local: `266` testes automatizados

| Módulo                    | Principais operações                                                                                  |
| ------------------------- | ----------------------------------------------------------------------------------------------------- |
| **Pedidos de venda**      | Buscar, criar, alterar status, cancelar, adicionar/remover itens, alterar preços                      |
| **Produtos**              | Consultar, atualizar dados, preços, custos, peso, NCM, saldos, grades, imagens                        |
| **Engenharia de produto** | Ficha de consumo, matéria-prima e serviços                                                            |
| **Clientes**              | Cadastrar, atualizar PF/PJ, consultar histórico e saldo financeiro                                    |
| **Financeiro (CR)**       | Títulos, boletos, link de pagamento, cheques-presente e vouchers                                      |
| **Financeiro (CP)**       | Duplicatas a pagar e comissões                                                                        |
| **Fiscal**                | NF-es, XMLs, DANFEs, manifestação e faturas                                                           |
| **Compras**               | Pedidos de compra e pacotes de entrada/saída                                                          |
| **Produção**              | Ordens de produção e consumo de matéria-prima                                                         |
| **Logística**             | Movimentações de material e lotes                                                                     |
| **Painéis rápidos**       | Dashboard do dia, visão 360, estoque disponível, vendas por canal, fluxo de caixa e pedidos em aberto |
| **Analytics / painéis**   | Gateway opcional para endpoints de Analytics, habilitado apenas por ambiente                          |
| **Inteligência de uso**   | Análise de padrões, sequências, horários de pico e sugestões de otimização                            |

---

## Segurança

Operações de leitura podem ser executadas diretamente.

Operações que criam, alteram, cancelam, baixam, estornam, removem ou excluem dados devem exigir confirmação explícita antes da execução.

Isso vale especialmente para:

* pedidos;
* clientes;
* produtos;
* títulos financeiros;
* notas fiscais;
* vouchers;
* preços;
* custos;
* movimentações.

A IA não deve alterar dados do ERP sozinha.

---

## Instalação

```bash
pip install totvs-moda-mcp
```

---

## Requisitos

* Python 3.11+
* API V2 do TOTVS Moda ativa na instância
* Credenciais OAuth2 de integração
* Cliente MCP compatível, como Claude Desktop, VS Code, GitHub Copilot Agent, Cursor ou similar
