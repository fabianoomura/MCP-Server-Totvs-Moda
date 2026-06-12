# Avancos v3.9

Data: 2026-06-12

## Resumo

A v3.9 fortalece o servidor MCP em tres frentes: confiabilidade operacional, reducao de contexto exposto ao cliente MCP e higiene de manutencao. O foco foi corrigir problemas reais sem alterar contratos publicos das tools.

## Entregas

### Cache apos escritas

As tools de escrita agora invalidam caches relacionados somente depois de uma chamada bem-sucedida. Isso evita leituras stale em consultas como pedidos, saldos, visoes 360 e paineis agregados.

Cobertura adicionada:
- update de preco invalida cache de produto/360 afetado;
- cancelamento de pedido invalida cache de pedidos;
- escrita com falha preserva o cache existente.

### Renovacao OAuth concorrente

`TotvsClient._ensure_token` passou a usar double-checked locking com `asyncio.Lock`. Chamadas simultaneas com token expirado agora compartilham uma unica renovacao, reduzindo chamadas desnecessarias ao endpoint de autenticacao.

### Perfis de exposicao

Foi criada a variavel `TOTVS_PROFILE` para controlar quais tools sao expostas:

- `completo`: comportamento padrao, todas as tools disponiveis;
- `leitura`: remove as tools anotadas como escrita;
- `vendedor`: consultas comerciais, produto, estoque, pedido, cliente e aggregators comerciais;
- `financeiro`: contas a receber/pagar, fiscal, voucher e aggregators financeiros;
- `gestor`: leituras e aggregators completos, sem writes anotadas.

Tambem foram adicionadas:

- `TOTVS_TOOLS_EXTRA`: adiciona tools individuais ao perfil;
- `TOTVS_TOOLS_EXCLUDE`: remove tools individuais do perfil.

O bloqueio acontece tanto em `handle_list_tools` quanto em `handle_call_tool`.

### Guardrails de manutencao

Novos testes garantem:

- toda tool exposta tem rota, exceto tools especiais tratadas inline;
- toda rota aponta para um metodo existente;
- a excecao conhecida `totvs_analytics_call` continua documentada porque depende de `TOTVS_ENABLE_ANALYTICS`.

### Modernizacoes

- `datetime.utcnow()` substituido por timestamps UTC timezone-aware;
- `hashlib.md5(..., usedforsecurity=False)` usado para chaves de cache;
- `.env.example` alinhado ao comportamento real de Analytics opt-in;
- `pyproject.toml` agora inclui extra `dev` para rodar a suite local.

## Validacao

Comandos executados:

```bash
pytest tests/ -q
pytest tests/ -q -W error::DeprecationWarning
```

Resultado:

```text
222 passed
```

Perfil vendedor:

```text
38 tools expostas
totvs_cancel_order ausente
```

Perfil completo:

```text
212 tools expostas
```

## Proximo passo recomendado

A refatoracao estrutural dos schemas para fora de `server.py` continua como proxima etapa. Ela deve ser feita separadamente por ter diff grande e exigir prova de equivalencia da ordem e do JSON dos schemas.
