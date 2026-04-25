# TOTVS Moda MCP Server

Integração MCP (Model Context Protocol) para a API V2 do TOTVS Moda.\
Projeto independente, construído por quem usa o sistema no dia a dia e
precisava resolver problemas reais.

Se fizer sentido pra você, use.\
Se encontrar problema, abra uma issue.\
Se quiser contribuir, PR é bem-vindo.

------------------------------------------------------------------------

## Contexto

Uso o TOTVS Moda desde 2021. No início, a curva de aprendizado foi alta.
Com o tempo, descobri as APIs e comecei a automatizar tarefas com Python
--- consultas, exportações, atualizações em lote.

O ganho de produtividade foi imediato.

Com a evolução dos LLMs e o surgimento do MCP (Model Context Protocol),
ficou claro que dava para ir além: permitir que uma IA interagisse
diretamente com o ERP.

Procurei uma solução pronta. Não existia --- nem oficial, nem da
comunidade.

Então construí.

Hoje uso esse projeto em produção no meu próprio trabalho. Ele evolui
conforme surgem necessidades reais.

------------------------------------------------------------------------

## O que você consegue fazer

Com um cliente MCP (Claude Desktop, VS Code Copilot, Cursor, etc.), você
pode consultar e operar o TOTVS usando linguagem natural.

Exemplos:

-   "Quais pedidos de venda foram criados hoje?"
-   "Qual o faturamento da semana passada por filial?"
-   "Quais produtos estão com saldo abaixo de 10?"
-   "Me mostra os 10 clientes que mais compraram este mês"
-   "Atualiza o preço do produto X para R\$ 89,90 na tabela 2"
-   "Quais títulos estão vencendo até sexta no contas a receber?"

------------------------------------------------------------------------

## Cobertura atual

-   18 módulos da API V2\
-   Mais de 75 tools disponíveis

Principais áreas:

-   Pedidos de venda\
-   Produtos\
-   Clientes\
-   Financeiro\
-   Fiscal\
-   Logística e produção\
-   Analytics (se contratado)

------------------------------------------------------------------------

## Por que usar

-   Redução de tempo operacional\
-   Eliminação de tarefas repetitivas\
-   Consulta e análise via linguagem natural\
-   Integração direta entre IA e ERP

------------------------------------------------------------------------

## Requisitos

-   Python 3.11+
-   API V2 do TOTVS Moda ativa
-   Credenciais de integração
-   Cliente MCP

------------------------------------------------------------------------

## Instalação

pip install totvs-moda-mcp

------------------------------------------------------------------------

## Configuração

Exemplo de mcp.json:

{ "servers": { "totvs-moda": { "command": "python", "args": \["-m",
"totvs_moda_mcp"\], "env": { "TOTVS_BASE_URL":
"https://seu-servidor:9443", "TOTVS_CLIENT_ID": "client_id",
"TOTVS_CLIENT_SECRET": "client_secret", "TOTVS_USERNAME": "usuario",
"TOTVS_PASSWORD": "senha", "TOTVS_BRANCH_CODES": "1" } } } }

------------------------------------------------------------------------

## Segurança

Evite expor credenciais no repositório:

"TOTVS_PASSWORD": "\${env:TOTVS_PASSWORD}"

------------------------------------------------------------------------

## Limitações

Limitado ao que a API V2 do TOTVS Moda expõe.

------------------------------------------------------------------------

## Como funciona

-   Autenticação OAuth2 com refresh automático\
-   Retry com backoff exponencial\
-   Tools organizadas por módulo\
-   Cache de contexto\
-   Preenchimento automático de parâmetros

------------------------------------------------------------------------

## Testes

pip install -r tests/requirements-test.txt\
PYTHONPATH=. pytest tests/ -v

------------------------------------------------------------------------

## Contribuição

-   Reporte bugs\
-   Sugira melhorias\
-   Envie PRs com testes

------------------------------------------------------------------------

## Licença

MIT

------------------------------------------------------------------------

## Contato

LinkedIn: https://www.linkedin.com/in/fabiano-o-50619734/
