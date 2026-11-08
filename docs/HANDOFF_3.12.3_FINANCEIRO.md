# Correção 3.12.3: contas a pagar zerado no fluxo de caixa e na posição vencida

**De:** clone `totvs-moda-mcp-tcloud-sp`, mesmo repositório GitHub (`fabianoomura/MCP-Server-Totvs-Moda`)
**Data:** 08/11/2026
**Situação neste clone:** ainda na 3.12.2, **com o defeito**
**Correção publicada:** `origin/main` em 08/11/2026, commit `ca549ee` (merge `1fd3365`). Para aplicar aqui, basta `git pull`.

## O defeito

`totvs_cash_flow_forecast` e `totvs_overdue_financial_summary` devolvem **contas a pagar = 0** em qualquer base.

- As duas pedem `pageSize` 500 ao `accounts-payable/v2/duplicates/search`.
- Esse endpoint só aceita até 100 e responde `400 FieldValueGreaterThan` ("Value 500 of the field PageSize greater than limit of 100").
- O `_safe()` engole o erro, e o lado a pagar sai vazio, **sem aviso**.
- Efeito: o fluxo de caixa aparece sempre positivo, e a posição vencida fica sem fornecedores.

**Confirmado nesta base (mooui) em 08/11:** de 09 a 22/11, `totvs_cash_flow_forecast` mostra a pagar = 0. A busca direta (`totvs_search_payable_duplicates`, `pageSize` 100) traz **58 títulos** na mesma janela.

Outros problemas das duas ferramentas, corrigidos juntos:
- **Só a página 1:** acima de 500 títulos, o total ficava cortado sem aviso.
- **Valor cheio:** o fluxo de caixa somava o valor cheio da duplicata, mesmo se já paga em parte.
- **Cache sem `pageSize`:** a chave do cache não inclui o `pageSize`. Por isso, repetir a chamada com `pageSize: 100` ainda devolve o resultado errado guardado.

## O que a 3.12.3 muda

Tudo está em `tools/aggregators.py`:

| Item | Mudança |
|---|---|
| Limites | `AP_MAX_PAGE_SIZE = 100` e `AR_MAX_PAGE_SIZE = 500` |
| `_collect_pages()` | Novo: pagina por `hasNext`/`totalPages`. **Não** usa `totalItems`, porque no contas a receber ele traz o tamanho da página, não o total. Devolve `{items, pages, truncated, error}` |
| Erro ou corte | O lado afetado vem com total `null` (não 0), `complete: false` e motivo em `warnings[]`. Resultado com aviso não vai para o cache |
| Fluxo de caixa | Usa saldo em aberto (valor − pago) e ignora parcela já liquidada. Novos campos: `payableByExpense`, `receivableByBillingType`, `receivableStatus`/`payableStatus` |
| Posição vencida | Ignora título com vencimento depois de `asOfDate`. Novos campos: `byBillingType` e `byBearer` no a receber (separa título em carteira de cobrança bancária) |
| Nomes | Preenche o nome de cliente e de fornecedor pelo cadastro de pessoa (PJ e PF) quando o título não traz. Novo `_person_names()` |
| Schema | Novos `maxPages` (nas duas) e `topN` (no fluxo de caixa). Descrições atualizadas |

Outros arquivos:
- **`server.py`:** `SERVER_VERSION = "3.12.3"`, mais um item no guia ("totais financeiros `null` não são zero").
- **`pyproject.toml`:** versão 3.12.3.
- **`CHANGELOG.md`:** entrada `[3.12.3]`.
- **`docs/FIELDS.md`:** nota sobre o limite de 100 do contas a pagar e o `totalItems`.
- **`tests/test_aggregators.py`:** 6 testes de regressão. Os 6 falham no código antigo.
- **`tests/test_tools_snapshot.py`:** hash do schema atualizado.

## Como trazer para cá

Os dois clones têm a mesma história, até o commit `c354a33`.

1. **A correção já está no `origin`:** rodar `git pull` neste clone. Ele está na `main` em `c354a33`, sem alteração de código, então o pull só avança (traz `8746343`, `ca549ee` e o merge `1fd3365`).
2. **Alternativa sem pull:**
   ```bash
   git fetch origin
   git cherry-pick ca549ee
   ```
3. **Testar:**
   ```bash
   python -m pytest -q tests -p no:cacheprovider --basetemp=<pasta temporária com permissão de escrita>
   ```
   O `--basetemp` evita o `PermissionError` na pasta `pytest-of-<usuário>`. Lá foram 272 testes passando.
4. **Reiniciar o MCP `totvs-moda`** (`/mcp` no Claude Code) para carregar o código novo.

## Conferência depois de aplicar

- `totvs_cash_flow_forecast` (startDate 2026-11-09, days 14): a pagar deve bater com a soma do saldo dos 58 títulos da busca direta, e `warnings` deve vir vazio.
- `totvs_overdue_financial_summary`: `payable.count` maior que zero, se houver duplicata vencida.
