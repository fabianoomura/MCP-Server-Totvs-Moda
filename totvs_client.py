"""
TOTVS Moda HTTP Client
======================
Handles authentication (OAuth2 Resource Owner Password Credentials)
and all HTTP communication with the TOTVS Moda API V2.
"""

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger("totvs-moda-mcp.client")

# Token endpoint pattern for TOTVS Moda
TOKEN_PATH = "/api/totvsmoda/authorization/v2/token"


class TotvsAuthError(Exception):
    """Raised when authentication fails."""


class TotvsApiError(Exception):
    """Raised when the TOTVS API returns an error."""

    def __init__(self, status_code: int, detail: Any):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"TOTVS API error {status_code}: {detail}")


class TotvsClient:
    """
    Async HTTP client for TOTVS Moda API V2.

    Handles:
    - OAuth2 ROPC token acquisition and automatic refresh
    - Base URL normalization
    - Error parsing from TOTVS DomainNotificationMessage format
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

        self._http = httpx.AsyncClient(
            timeout=timeout,
            verify=False,  # Some TOTVS instances use self-signed certs
        )

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
    # HTTP helpers
    # ------------------------------------------------------------------

    def _parse_error(self, response: httpx.Response) -> Any:
        """Try to extract meaningful error from TOTVS DomainNotificationMessage."""
        try:
            body = response.json()
            # TOTVS error format: {"messages": [{"message": "...", "severity": "Error"}]}
            if "messages" in body:
                msgs = [m.get("message", "") for m in body["messages"]]
                return " | ".join(msgs)
            return body
        except Exception:
            return response.text

    async def get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self.base_url}{path}"
        headers = await self._headers()
        logger.debug(f"GET {url} params={params}")

        response = await self._http.get(url, headers=headers, params=params)

        if response.status_code >= 400:
            raise TotvsApiError(response.status_code, self._parse_error(response))

        return response.json()

    async def post(self, path: str, body: dict) -> Any:
        url = f"{self.base_url}{path}"
        headers = await self._headers()
        logger.debug(f"POST {url} body={body}")

        response = await self._http.post(url, headers=headers, json=body)

        if response.status_code >= 400:
            raise TotvsApiError(response.status_code, self._parse_error(response))

        # Some endpoints return 200/201 with empty body
        if not response.content:
            return {"success": True, "statusCode": response.status_code}

        return response.json()

    async def delete(self, path: str, params: dict | None = None) -> Any:
        url = f"{self.base_url}{path}"
        headers = await self._headers()
        logger.debug(f"DELETE {url} params={params}")

        response = await self._http.delete(url, headers=headers, params=params)

        if response.status_code >= 400:
            raise TotvsApiError(response.status_code, self._parse_error(response))

        if not response.content:
            return {"success": True, "statusCode": response.status_code}

        return response.json()

    async def aclose(self) -> None:
        await self._http.aclose()
