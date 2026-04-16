# Publicando no PyPI

Guia passo a passo para publicar o `totvs-moda-mcp` no PyPI.

## Pré-requisitos

```bash
pip install hatch twine
```

Crie sua conta em https://pypi.org e gere um API token em:
**Account settings → API tokens → Add API token**

## Publicação

### 1. Atualizar a versão

Em `pyproject.toml`, incremente o campo `version`:

```toml
version = "2.0.1"  # patch
version = "2.1.0"  # minor (novos módulos)
version = "3.0.0"  # major (breaking changes)
```

### 2. Build

```bash
hatch build
```

Isso gera a pasta `dist/` com os arquivos `.whl` e `.tar.gz`.

### 3. Publicar

```bash
twine upload dist/*
```

Informe seu token PyPI quando solicitado (no lugar do password).

### 4. Testar a instalação

```bash
pip install totvs-moda-mcp
```

---

## Após publicar

Atualize o README com o badge de instalação:

```markdown
[![PyPI](https://img.shields.io/pypi/v/totvs-moda-mcp)](https://pypi.org/project/totvs-moda-mcp/)
```

E atualize a seção de instalação:

```markdown
## Instalação

pip install totvs-moda-mcp
```

---

## Configuração após pip install

Com o pacote instalado globalmente, configure o cliente MCP assim:

```json
{
  "mcpServers": {
    "totvs-moda": {
      "command": "totvs-moda-mcp",
      "env": {
        "TOTVS_BASE_URL": "https://seu-servidor:9443",
        "TOTVS_CLIENT_ID": "",
        "TOTVS_CLIENT_SECRET": "",
        "TOTVS_USERNAME": "",
        "TOTVS_PASSWORD": "",
        "TOTVS_BRANCH_CODES": "1"
      }
    }
  }
}
```

Sem clonar repositório, sem path absoluto — só `pip install` e configurar as variáveis.
