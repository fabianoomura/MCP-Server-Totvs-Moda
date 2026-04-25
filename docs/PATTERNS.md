# TOTVS Moda MCP Server — Padrões Obrigatórios

> Padrões que **devem** ser seguidos em qualquer mudança no projeto. Cole isso em qualquer thread futura antes de pedir implementação.

---

## 1. Padrão de Tool de Busca (search)

**Toda tool que faz `POST /xxx/search` ou `GET /xxx?filtro=...` deve seguir este padrão:**

```python
# tools/<modulo>.py

from typing import Any
from totvs_client import TotvsClient
from tools._defaults import inject_branch_defaults  # se precisa de branchCode
from tools._fields import apply_fields

BASE = "/api/totvsmoda/<modulo>/v2"


class XxxTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_xxx(self, args: dict[str, Any]) -> Any:
        """POST /xxx/search — Descrição."""
        # 1. Default injection (se aplicável)
        args = inject_branch_defaults(args)
        
        # 2. Build filter excluindo campos especiais
        excluded = ("page", "pageSize", "order", "fields")
        flt = {k: v for k, v in args.items() if k not in excluded and v is not None}
        
        # 3. Build body com paginação
        body: dict[str, Any] = {
            "filter": flt,
            "page": args.get("page", 1),
            "pageSize": args.get("pageSize", 100),
        }
        if args.get("order"):
            body["order"] = args["order"]
        
        # 4. Chamar API
        result = await self.client.post(f"{BASE}/xxx/search", body)
        
        # 5. Aplicar fields filter (último passo)
        return apply_fields(result, args)
```

**Por que cada passo:**

- `inject_branch_defaults` (passo 1): preenche `branchCode` automaticamente se o LLM esquecer. Evita erros 400 em loop.
- `excluded` tuple (passo 2): campos especiais (`page`, `pageSize`, `order`, `fields`) não vão pra dentro de `filter` — eles têm posição própria no body ou são metadata interna.
- Filtro `if v is not None` (passo 2): permite que LLM passe `null` explícito sem virar filtro.
- `apply_fields` (passo 5): se LLM passou `fields=[...]`, retorna versão enxuta. Senão retorna tudo.

---

## 2. Padrão de Tool de Escrita (create / update / cancel)

**Toda tool que muda dados no TOTVS deve seguir este padrão:**

```python
async def update_xxx(self, args: dict[str, Any]) -> Any:
    """PUT /xxx — ⚠️ Altera dados de xxx."""
    # 1. Default injection (se aplicável)
    args = inject_branch_defaults(args)
    
    # 2. Filtro genérico (aceita qualquer campo passado)
    body = {k: v for k, v in args.items() if v is not None}
    
    # 3. Chamar API
    return await self.client.put(f"{BASE}/xxx", body)
```

**Princípio importante:** o método Python deve aceitar **qualquer campo via filtro genérico** (`{k: v for k, v in args.items()}`). Não fazer hardcode tipo `body = {"description": args.get("description")}`. 

**Por quê?** O schema do MCP no `server.py` é o que limita o LLM. Se você expõe novo campo no schema, o método Python já aceita automaticamente — sem precisar mexer no código Python. Isso facilita ampliação futura.

---

## 3. Padrão de Tool no `server.py`

**Toda tool registrada no `server.py` deve ter:**

```python
types.Tool(
    name="totvs_xxx",  # snake_case com prefixo totvs_
    description=(
        "Descrição rica e útil. Retorna items[] com: campo1, campo2, campo3. "
        "Para xxx use totvs_yyy. Para zzz use totvs_aggregator_xxx. "
        "Use fields=['campo1','campo2'] para reduzir tokens."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "obrigatorio_1": {"type": "integer", "description": "..."},
            "opcional_1": {"type": "string", "description": "..."},
            # Sempre incluir 'fields' nas tools de busca:
            "fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Lista opcional de campos a retornar. Reduz tokens."
            },
            # Em busca, sempre incluir page/pageSize:
            "page": {"type": "integer", "default": 1},
            "pageSize": {"type": "integer", "default": 100},
        },
        "required": ["obrigatorio_1"]  # só os realmente obrigatórios pela API
    }
),
```

**Regras das descrições:**

- Mencionar shape do retorno (campos principais)
- Redirecionar pra tools melhores quando aplicável
- Mencionar `fields=[...]` em tools de busca
- Avisar sobre escrita com `⚠️ ESCRITA — ...` no início
- Documentar enums e valores aceitos

---

## 4. Padrão de Routing

**No `server.py`, cada tool tem entrada no dicionário `ROUTING`:**

```python
ROUTING: dict[str, tuple[str, str]] = {
    "totvs_xxx_yyy": ("modulo", "metodo_python"),
    # ...
}
```

A primeira string é o nome da tool MCP (com prefixo `totvs_`). A tupla aponta pro módulo (chave em `get_modules()`) e o método Python.

---

## 5. Padrão de Teste

**Todo endpoint novo precisa de teste em `tests/`:**

```python
# tests/test_xxx.py

import pytest
import respx
from httpx import Response

from conftest import TOTVS_BASE, TOKEN_URL


@pytest.mark.asyncio
@respx.mock
async def test_xxx_endpoint_works(client):
    """Validates that totvs_xxx_yyy calls the right URL with right body."""
    # 1. Mock OAuth
    respx.post(TOKEN_URL).mock(
        return_value=Response(200, json={
            "access_token": "fake", "expires_in": 3600, "token_type": "Bearer"
        })
    )
    
    # 2. Mock target endpoint
    route = respx.post(f"{TOTVS_BASE}/api/totvsmoda/xxx/v2/yyy").mock(
        return_value=Response(200, json={"items": [...], "totalHits": 1})
    )
    
    # 3. Setup tool
    from tools.xxx import XxxTools
    tools = XxxTools(client)
    
    # 4. Call
    result = await tools.method_name({"branchCode": 1, "param": "value"})
    
    # 5. Assert response shape
    assert result["totalHits"] == 1
    
    # 6. Assert request was made correctly
    assert route.called
    request_body = route.calls.last.request.content
    # ... validar body, headers, etc
```

---

## 6. Padrão de Conftest

`tests/conftest.py` provê fixtures globais. **Não modificar sem entender o impacto.**

Fixtures importantes:
- `client` — TotvsClient mockado pra cada teste
- `_env_setup` — env vars determinísticos (autouse)
- `fake_context_cache_global` — context_cache fake com `branches=[1]` (autouse, mas pode ser sobrescrito por teste-específico)

---

## 7. Padrão de Versão

| Tipo de mudança | Bump |
|-----------------|------|
| Adicionar tool nova | minor (3.0.0 → 3.1.0) |
| Adicionar campo no schema | patch (3.1.0 → 3.1.1) |
| Fix de bug em tool existente | patch (3.1.0 → 3.1.1) |
| Mudar nome de tool ou required de schema | major (3.x.x → 4.0.0) |
| Remover tool ou módulo | major (3.x.x → 4.0.0) |

---

## 8. Padrão de Commit

```
tipo: descrição curta (max 72 chars)

Descrição mais longa explicando o que e por quê (se necessário).

- Bullet point 1
- Bullet point 2
```

**Tipos:**
- `feat:` — funcionalidade nova
- `fix:` — bug fix
- `docs:` — só documentação
- `refactor:` — sem mudança funcional
- `test:` — só testes
- `chore:` — manutenção, dependências, configs

---

## 9. Padrão de PyPI release

Antes de publicar:

```powershell
# Limpar builds antigos
Remove-Item -Recurse -Force dist, build, *.egg-info -ErrorAction SilentlyContinue

# Build
hatch build

# Validar
twine check dist/*

# Publicar
twine upload dist/*
```

Observações:
- PyPI não permite republicar a mesma versão. Bump sempre antes.
- README é "baked in" no build — não tem como atualizar README sem nova versão.

---

## 10. Padrão de Resposta a Issues e PRs no GitHub

(quando o projeto receber issues/PRs externos)

- Responder em até 7 dias mesmo que seja "vou olhar quando der tempo"
- PRs precisam:
  - Ter teste novo se adiciona endpoint
  - Não quebrar testes existentes
  - Seguir os padrões deste documento
- Issues:
  - Pedir reprodução mínima
  - Dizer se vai consertar ou se é bug da API TOTVS

---

## Anti-padrões — coisas a NÃO fazer

❌ **Hardcode de campos no método Python** (impede expansão fácil via schema)
❌ **Tool sem `inject_branch_defaults` quando endpoint precisa de branch** (gera loop 400)
❌ **Tool de search sem `apply_fields`** (gasta tokens à toa)
❌ **Descrição genérica ("busca xxx")** (LLM chuta nomes de campo)
❌ **Lógica MOOUI no código público** (vira script privado)
❌ **Adicionar dependência sem necessidade** (mantém o projeto leve)
❌ **Mudar nome de tool existente** (quebra config dos usuários)
❌ **Tool sem teste** (regressões silenciosas)

---

## Checklist antes de commitar

- [ ] Método Python segue padrão correto (search ou write)
- [ ] Tool registrada no `server.py` com schema rico
- [ ] Entrada no ROUTING dict
- [ ] `inject_branch_defaults` aplicado se precisar
- [ ] `apply_fields` aplicado se for search
- [ ] Teste em `tests/`
- [ ] Suite completa passando (`pytest tests/ -v`)
- [ ] CHANGELOG atualizado
- [ ] Versão bumpada no `pyproject.toml`
- [ ] README atualizado se for mudança visível ao usuário final
