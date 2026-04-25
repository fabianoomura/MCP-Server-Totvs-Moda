# Pacote de Documentação — TOTVS Moda MCP Server

## O que é este pacote

Este é o pacote de documentação do projeto **TOTVS Moda MCP Server**. O objetivo dele é permitir que você (Fabiano) **retome o desenvolvimento em qualquer thread futura com Claude** sem precisar reexplicar tudo do zero.

A conversa em que esse projeto evoluiu já está bem extensa, e fazer mais ampliações na mesma thread vai degradar a qualidade. A solução é abrir threads novas focadas em fases específicas, e o conteúdo aqui dentro é o ponto de partida.

---

## Conteúdo

### Documentos fundamentais (sempre colar em thread nova)

1. **`PROJECT_STATE.md`** — Estado completo do projeto, histórico de versões, decisões tomadas, próximos passos.

2. **`ROADMAP.md`** — Plano de fases v3.x.0 com prioridades e estimativas.

3. **`PATTERNS.md`** — Padrões obrigatórios de código (search, write, schema, testes, versão).

### Documentos da fase atual

4. **`MIGRATION_v3.0.md`** — Manual passo-a-passo da migração v2.6.1 → v3.0.0 (remoção do analytics).

---

## Como usar

### Para aplicar a v3.0.0 agora

1. Abra o Copilot Chat / Claude Code no VS Code do projeto
2. Cole esta mensagem:

```
Vou aplicar a v3.0.0 do projeto MCP TOTVS Moda. Esta versão remove o
módulo Analytics completamente.

Leia os arquivos abaixo nesta ordem:
1. docs/PATTERNS.md — entenda os padrões do projeto
2. docs/MIGRATION_v3.0.md — siga as 12 etapas

Execute as 12 etapas do MIGRATION_v3.0.md em ordem.

Regras:
- Faça backup das mudanças (`.bak` ou git branch separado)
- Rode pytest depois de cada arquivo modificado
- Pare se algum teste quebrar
- Esperado ao final: 91 tests passing, 24 tools de analytics removidas
```

3. Acompanhe o trabalho. Em ~30-45 min está pronto.

### Para abrir uma fase nova em outra thread

1. Inicie nova conversa com Claude (claude.ai ou Claude Code)
2. Cole esta sequência:

```
Estou retomando o projeto MCP Server TOTVS Moda. Anexo abaixo o
contexto completo.

[Cole todo o conteúdo de PROJECT_STATE.md aqui]

[Cole todo o conteúdo de ROADMAP.md aqui]

[Cole todo o conteúdo de PATTERNS.md aqui]

Quero executar a fase v3.X.0 (escolha a fase do roadmap).

Anexei o JSON da Postman collection do módulo: [arquivo .json]

Vamos começar pela auditoria: comparar o que está em tools/X.py
e server.py contra o JSON, e gerar lista de gaps. Não implemente
nada ainda — só auditoria.
```

3. Anexe o JSON correto (ver tabela no `ROADMAP.md`)

4. Claude na nova thread vai ter contexto completo

---

## Fluxo recomendado das próximas threads

```
Thread atual (essa) → v3.0.0 (analytics removido)
   ↓
Thread nova #1     → v3.1.0 (Product completo) ← prioridade máxima
   ↓
Thread nova #2     → v3.2.0 (Accounts Receivable completo)
   ↓
Thread nova #3     → v3.3.0 (Accounts Payable completo)
   ↓
Thread nova #4     → v3.4.0 (Fiscal completo)
   ↓
Thread nova #5     → v3.5.0 (Person completo)
   ↓
Thread nova #6     → v3.6.0 (Sales Order endpoints faltantes)
   ↓
Thread nova #7     → v3.7.0 (módulos pequenos consolidados)
   ↓
Thread nova #8     → v3.8.0 (release final + PyPI)
```

Você não precisa fazer todas. Pode parar em v3.1.0 se quiser e voltar depois.

---

## Princípios

**Fazer poucas coisas bem feitas é melhor que muitas coisas mal feitas.** Cada fase deve sair completa antes de pular pra próxima — com testes, manual, commit, push, e idealmente publicação no PyPI.

**Cada thread deve sair com algo testável.** Não terminar uma thread sem ter "rodou pytest e passou 91+ tests".

**Documentação atualizada é parte da entrega.** Se uma fase adiciona 50 endpoints, o README precisa refletir. CHANGELOG idem. Não deixar pra depois.

---

## Sobre as credenciais

⚠️ As credenciais TOTVS apareceram nas threads anteriores (`TOTVS_CLIENT_SECRET=7556720068`, `TOTVS_PASSWORD=654321`). **Trocar no TOTVS antes de continuar usando o projeto**, caso ainda não tenha trocado. Atualizar o `mcp.json` com os valores novos.

---

## Pronto pra começar?

A próxima ação imediata é aplicar a v3.0.0 (remoção do analytics). Use o `MIGRATION_v3.0.md` no Claude Code do VS Code.

Depois disso, você terá um projeto limpo (~111 tools), bem documentado, e com plano claro pra crescer.
