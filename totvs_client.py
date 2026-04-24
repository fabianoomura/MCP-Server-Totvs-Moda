"""
TOTVS Moda HTTP Client
======================
Handles authentication (OAuth2 Resource Owner Password Credentials)
and all HTTP communication with the TOTVS Moda API V2.
"""

import asyncio
import logging
import os
import time
from typing import Any

import httpx

logger = logging.getLogger("totvs-moda-mcp.client")

# Token endpoint pattern for TOTVS Moda
TOKEN_PATH = "/api/totvsmoda/authorization/v2/token"

# Backoff base in seconds for 5xx / network retries.
# Tests monkeypatch this to 0.0 for fast execution.
DEFAULT_BACKOFF_BASE = 0.5


class TotvsAuthError(Exception):
    """Raised when authentication fails."""


class TotvsApiError(Exception):
    """Raised when the TOTVS API returns an error."""

    def __init__(self, status_code: int, detail: Any, codes: list[str] | None = None):
        self.status_code = status_code
        self.detail = detail
        self.codes: list[str] = codes or []
        super().__init__(f"TOTVS API error {status_code}: {detail}")

    def has_code(self, code: str) -> bool:
        """Return True if any TOTVS message contains the given code string.

        Checks the structured codes list first, then falls back to a
        substring search in the detail text (for unstructured error bodies).
        """
        if code in self.codes:
            return True
        return code in str(self.detail)


class TotvsClient:
    """
    Async HTTP client for TOTVS Moda API V2.

    Handles:
    - OAuth2 ROPC token acquisition and automatic refresh
    - Base URL normalization
    - Error parsing from TOTVS DomainNotificationMessage format
    - Reactive 401 retry (token invalidated by server before expiry)
    - 5xx and network error retry with exponential backoff
    """

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.timeout = timeout

        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

        # TLS verification: enabled by default.
        # Set TOTVS_TLS_VERIFY=false only if the server uses a self-signed
        # certificate and you accept the MITM risk on your network.
        tls_verify: bool = os.getenv("TOTVS_TLS_VERIFY", "true").lower() not in ("false", "0", "no")

        self._http = httpx.AsyncClient(
            timeout=timeout,
            verify=tls_verify,
        )

        self._max_retries: int = int(os.getenv("TOTVS_MAX_RETRIES", "3"))

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    async def _ensure_token(self) -> str:
        """Return a valid access token, refreshing if necessary."""
        if self._access_token and time.time() < self._token_expires_at - 30:
            return self._access_token

        logger.info("Acquiring TOTVS access token...")
        url = f"{self.base_url}{TOKEN_PATH}"

        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password,
            "scope": "openid",
        }

        response = await self._http.post(url, data=data)

        if response.status_code != 200:
            raise TotvsAuthError(
                f"Falha na autenticação TOTVS (HTTP {response.status_code}): "
                f"{response.text}"
            )

        token_data = response.json()
        self._access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600)
        self._token_expires_at = time.time() + expires_in

        logger.info(f"Token adquirido. Expira em {expires_in}s.")
        return self._access_token

    async def _headers(self) -> dict[str, str]:
        token = await self._ensure_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ------------------------------------------------------------------
    # Error parsing
    # ------------------------------------------------------------------

    def _parse_error(self, response: httpx.Response) -> tuple[Any, list[str]]:
        """Parse TOTVS DomainNotificationMessage, returning (detail, codes)."""
        try:
            body = response.json()
            if "messages" in body:
                msgs = body["messages"]
                codes = [m.get("code", "") for m in msgs if m.get("code")]
                text = " | ".join(m.get("message", "") for m in msgs)
                return text, codes
            return body, []
        except Exception:
            return response.text, []

    def _raise_for_error(self, response: httpx.Response) -> None:
        if response.status_code >= 400:
            detail, codes = self._parse_error(response)
            raise TotvsApiError(response.status_code, detail, codes)

    # ------------------------------------------------------------------
    # Core request with retry
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict | None = None,
        params: dict | None = None,
        _auth_retried: bool = False,
        _retries_left: int | None = None,
    ) -> Any:
        if _retries_left is None:
            _retries_left = self._max_retries

        url = f"{self.base_url}{path}"
        headers = await self._headers()

        try:
            response = await self._http.request(
                method, url, headers=headers, json=body, params=params
            )
        except (httpx.TimeoutException, httpx.NetworkError):
            if _retries_left > 0:
                await asyncio.sleep(DEFAULT_BACKOFF_BASE)
                return await self._request(
                    method, path, body=body, params=params,
                    _auth_retried=_auth_retried, _retries_left=_retries_left - 1,
                )
            raise

        # Reactive 401: token invalidated by server before cache expiry
        if response.status_code == 401 and not _auth_retried:
            self._access_token = None
            self._token_expires_at = 0.0
            return await self._request(
                method, path, body=body, params=params,
                _auth_retried=True, _retries_left=_retries_left,
            )

        # 5xx: retry with exponential backoff
        if response.status_code >= 500 and _retries_left > 0:
            attempt = self._max_retries - _retries_left
            await asyncio.sleep(DEFAULT_BACKOFF_BASE * (2 ** attempt))
            return await self._request(
                method, path, body=body, params=params,
                _auth_retried=_auth_retried, _retries_left=_retries_left - 1,
            )

        self._raise_for_error(response)

        if not response.content:
            return {"success": True, "statusCode": response.status_code}

        return response.json()

    # ------------------------------------------------------------------
    # HTTP methods
    # ------------------------------------------------------------------

    async def get(self, path: str, params: dict | None = None) -> Any:
        logger.debug(f"GET {path} params={params}")
        return await self._request("GET", path, params=params)

    async def post(self, path: str, body: dict) -> Any:
        logger.debug(f"POST {path}")
        return await self._request("POST", path, body=body)

    async def put(self, path: str, body: dict) -> Any:
        logger.debug(f"PUT {path}")
        return await self._request("PUT", path, body=body)

    async def delete(self, path: str, params: dict | None = None) -> Any:
        logger.debug(f"DELETE {path} params={params}")
        return await self._request("DELETE", path, params=params)

    # ------------------------------------------------------------------
    # Convenience: create-or-update pattern
    # ------------------------------------------------------------------

    async def upsert(self, update_path: str, create_path: str, body: dict) -> dict:
        """Try update first; fall back to create if record doesn't exist.

        Returns {"operation": "updated"|"created", "result": <api response>}.
        Raises TotvsApiError for any error other than NotFound.
        """
        try:
            result = await self.post(update_path, body)
            return {"operation": "updated", "result": result}
        except TotvsApiError as exc:
            if exc.has_code("NotFound"):
                result = await self.post(create_path, body)
                return {"operation": "created", "result": result}
            raise

    async def aclose(self) -> None:
        await self._http.aclose()
