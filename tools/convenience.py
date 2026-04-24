"""
Convenience Tools
=================
High-level tools that wrap raw TOTVS API calls with extra logic —
input normalisation, routing, create-or-update fallback patterns.

These tools exist because the LLM shouldn't need to know whether a
customer is PF or PJ before searching, or whether a product value
already exists before deciding to call create vs update.
"""
import re
from typing import Any

from totvs_client import TotvsClient, TotvsApiError

BASE_PERSON = "/api/totvsmoda/person/v2"
BASE_PRODUCT = "/api/totvsmoda/product/v2"


class ConvenienceTools:
    def __init__(self, client: TotvsClient) -> None:
        self.client = client

    async def search_customer_by_document(self, args: dict[str, Any]) -> Any:
        """Busca cliente por CPF ou CNPJ sem precisar saber se é PF ou PJ.

        Detecta automaticamente pelo tamanho do documento (11 dígitos = CPF,
        14 dígitos = CNPJ) e roteia para o endpoint correto.

        Args:
            document (required): CPF ou CNPJ (com ou sem máscara)

        Returns:
            Resultado do endpoint correspondente com campos extras:
            _documentType ("CPF" | "CNPJ") e _documentClean (só dígitos)
        """
        raw = args.get("document", "")
        digits = re.sub(r"\D", "", raw)

        if len(digits) == 11:
            doc_type = "CPF"
            endpoint = f"{BASE_PERSON}/individuals/search"
            body = {"filter": {"cpfCnpj": digits}, "page": 1, "pageSize": 10}
        elif len(digits) == 14:
            doc_type = "CNPJ"
            endpoint = f"{BASE_PERSON}/legal-entities/search"
            body = {"filter": {"cpfCnpj": digits}, "page": 1, "pageSize": 10}
        else:
            raise ValueError(
                f"Documento inválido: {raw!r}. "
                "CPF deve ter 11 dígitos e CNPJ deve ter 14 dígitos."
            )

        result = await self.client.post(endpoint, body)
        if isinstance(result, dict):
            result["_documentType"] = doc_type
            result["_documentClean"] = digits
        return result

    async def upsert_product_value(self, args: dict[str, Any]) -> Any:
        """Cria ou atualiza um valor de produto (create-or-update).

        Tenta update primeiro; se o registro não existir (400/NotFound),
        cai no create. Retorna {"operation": "updated"|"created", ...resultado}.

        Args:
            branchCode (required): Código da filial
            productCode (required): Código do produto
            valueCode (required): Código do tipo de valor
            value (required): Valor numérico
        """
        payload = {k: v for k, v in args.items() if v is not None}

        try:
            result = await self.client.post(f"{BASE_PRODUCT}/values/update", payload)
            return {"operation": "updated", **result} if isinstance(result, dict) else {"operation": "updated", "result": result}
        except TotvsApiError as exc:
            if exc.has_code("NotFound"):
                result = await self.client.post(f"{BASE_PRODUCT}/values/create", payload)
                return {"operation": "created", **result} if isinstance(result, dict) else {"operation": "created", "result": result}
            raise
