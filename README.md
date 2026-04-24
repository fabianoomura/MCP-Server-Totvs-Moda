# TOTVS Moda MCP Server

MCP Server para a API V2 do TOTVS Moda. Projeto pessoal, não oficial, feito por um usuário do sistema que resolveu aprender a programar pra facilitar a própria vida.

Se te servir, ótimo. Se achou bug, abre issue. Se quer contribuir, PR é bem-vindo.

[![PyPI](https://img.shields.io/pypi/v/totvs-moda-mcp.svg)](https://pypi.org/project/totvs-moda-mcp/)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Por que existe

Sou usuário do TOTVS Moda desde o final de 2021. Tive dificuldade pra entender o sistema no começo, depois descobri as APIs, estudei por conta, e comecei a escrever scripts Python pra acelerar tarefas repetitivas no trabalho — consultas, exportações, atualizações em lote. Economizou muito tempo.

Quando os LLMs avançaram e a Anthropic lançou o MCP (Model Context Protocol — padrão pra conectar IA a sistemas externos), pensei: dava pra conectar com TOTVS Moda.

Fui procurar se já existia. Não existia — nem oficial, nem de parceiros, nem da comunidade. Então fiz.

O projeto não é oficial da TOTVS. Não tem time por trás. Sou só eu, trabalhando na hora que dá. Uso em produção no meu próprio trabalho, e vou corrigindo o que quebra. Compartilho porque outras empresas que usam TOTVS Moda provavelmente têm a mesma dor.

## O que dá pra fazer

Com o MCP conectado ao Claude (ou qualquer cliente MCP — Claude Desktop, Claude Code, VS Code Copilot, Cursor), você pergunta em linguagem natural e ele consulta ou age no TOTVS.

Exemplos de perguntas que funcionam hoje:

- "Quais pedidos de venda foram criados hoje?"
- "Qual o faturamento da semana passada por filial?"
- "Me mostra as estatísticas de compra do cliente 38181"
- "Quais produtos estão com saldo abaixo de 10?"
- "Quais os 10 clientes que mais compraram este mês?"
- "Atualiza o preço do produto X para R$ 89,90 na tabela de preço 2"
- "Me dá os documentos em aberto no contas a receber com vencimento até sexta"

Cobertura atual: 18 módulos da API V2, mais de 75 tools.

- **Pedidos de venda**: consulta, criação B2C, cancelamento, alteração de itens, transporte, observações
- **Produtos**: busca, preços, custos, saldos, referências, cores, grades, lotes
- **Clientes**: PF/PJ, representantes, bônus, estatísticas, mensagens
- **Financeiro**: contas a receber e a pagar com cobertura 100% do swagger
- **Fiscal**: NF-e, XML, DANFE, centros de custo
- **Logística, vouchers, imagens, pacotes de dados, ordens de produção, ordens de compra**
- **Analytics** (se sua empresa tem o módulo contratado): movimentação fiscal, painel financeiro, painel de vendedor

## Requisitos

- Python 3.11 ou superior
- Uma instância do TOTVS Moda V2 com API ativada
- Credenciais de integração (client_id, client_secret, usuário, senha)
- Um cliente MCP (Claude Desktop, Claude Code, VS Code Copilot Chat em modo Agent, Cursor, etc.)

## Instalação

```bash
pip install totvs-moda-mcp
```

## Configuração

Exemplo de configuração para VS Code Copilot Chat (`mcp.json`):

```json
{
  "servers": {
    "totvs-moda": {
      "command": "python",
      "args": ["-m", "totvs_moda_mcp"],
      "env": {
        "TOTVS_BASE_URL": "https://seu-servidor-totvs:9443",
        "TOTVS_CLIENT_ID": "seu_client_id",
        "TOTVS_CLIENT_SECRET": "seu_secret",
        "TOTVS_USERNAME": "seu_usuario",
        "TOTVS_PASSWORD": "sua_senha",
        "TOTVS_BRANCH_CODES": "1"
      }
    }
  }
}
```

Para Claude Desktop, a estrutura é igual, só muda a chave raiz para `mcpServers` em vez de `servers`.

### Variáveis de ambiente

**Obrigatórias:**

| Variável              | Descrição                                                              |
| --------------------- | ---------------------------------------------------------------------- |
| `TOTVS_BASE_URL`      | URL base da sua API TOTVS (ex: `https://www30.suaempresa.com.br:9443`) |
| `TOTVS_CLIENT_ID`     | Client ID da integração                                                |
| `TOTVS_CLIENT_SECRET` | Client secret                                                          |
| `TOTVS_USERNAME`      | Usuário de integração no TOTVS                                         |
| `TOTVS_PASSWORD`      | Senha do usuário                                                       |

**Recomendadas:**

| Variável             | Padrão | Descrição                                                                                               |
| -------------------- | ------ | ------------------------------------------------------------------------------------------------------- |
| `TOTVS_BRANCH_CODES` | —      | Filial padrão (ex: `1` ou `1,2,5`). Se não setar, toda chamada com filial vai exigir o código explícito |

**Opcionais:**

| Variável                 | Padrão | Descrição                                                               |
| ------------------------ | ------ | ----------------------------------------------------------------------- |
| `TOTVS_TIMEOUT`          | `30`   | Timeout em segundos por chamada                                         |
| `TOTVS_MAX_RETRIES`      | `3`    | Tentativas em erros 5xx e rede                                          |
| `TOTVS_TLS_VERIFY`       | `true` | Verificação TLS (só mude se seu servidor usa certificado auto-assinado) |
| `TOTVS_ENABLE_ANALYTICS` | `true` | Desabilita o módulo Analytics se sua empresa não contrata               |

### Segurança das credenciais

**Não comite o `mcp.json` com credenciais reais.** Uma opção segura é referenciar variáveis de ambiente do sistema operacional:

```json
"env": {
  "TOTVS_PASSWORD": "${env:TOTVS_PASSWORD}"
}
```

## Limitações conhecidas

Esse projeto é limitado pelo que a API V2 do TOTVS Moda expõe.

## Como funciona por dentro

Em linhas gerais:

1. Autenticação OAuth2 ROPC contra `/api/totvsmoda/authorization/v2/token`, com refresh automático quando o token expira
2. Retry automático em 401 reativo (token invalidado antes da hora pelo servidor) e em 5xx com backoff exponencial
3. Cada módulo da API tem um arquivo em `tools/` que expõe os endpoints como métodos async
4. `server.py` registra as tools MCP, mapeia argumentos pros métodos, e retorna JSON pro cliente
5. `context_cache.py` carrega dados de referência no startup (filiais, operações, tabelas de preço) pra evitar chamadas repetidas
6. `tools/_defaults.py` preenche automaticamente `branchCode` da variável de ambiente quando o LLM esquece de passar — reduz drasticamente os erros 400 em loop

Se você quiser entender a arquitetura em mais detalhe, dê uma olhada no `server.py` e no `totvs_client.py`. O código é comentado em português.

## Testes

O projeto tem testes automatizados cobrindo as tools, o client HTTP, e os utilitários de injeção de default e filtragem de campos.

```bash
pip install -r tests/requirements-test.txt
PYTHONPATH=. pytest tests/ -v
```

## Contribuindo

Se você usa TOTVS Moda e quer ajudar:

- **Bug ou endpoint que não funciona?** Me envie mensagem descrevendo o que você tentou e o que aconteceu.

- **Quer mandar código?** PRs são bem-vindos. O projeto tem teste automatizado — se você adicionar um endpoint novo, adicione um teste junto (tem exemplos em `tests/`).

## Licença

MIT. Usa à vontade. Se quiser dar crédito, ótimo, mas não é obrigatório.

## Contato

[LinkedIn](https://www.linkedin.com/in/fabiano-o-50619734/) — se quiser conversar sobre TOTVS, integração com IA, ou só falar que o projeto te ajudou.
