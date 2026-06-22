"""Direct-to-gateway HTTP helpers (not part of the engine query/execute protocol).

These hit plain gateway routes (`/ip`, `/cf-check`, `/time`) used for connectivity
and geo/IP gating checks, mirroring the TypeScript SDK's `EngineWebClient`.
"""

from typing import Optional

import requests

COUNTRY_HEADER = "x-nado-country"

# One of "query_only", "blocked", or None when the IP is not restricted.
IpBlockStatus = Optional[str]


class EngineWebClient:
    """Client for unauthenticated gateway connectivity/geo endpoints."""

    def __init__(self, url: str):
        self.url = url.rstrip("/")
        self.session = requests.Session()

    def get_ip_block_status(self) -> IpBlockStatus:
        """Return the caller's IP block status, or None if not restricted.

        Reads the `/ip` endpoint; a 403 with `blocked: true` indicates a
        restriction (`query_only` when the reason is `ip_query_only`, else
        `blocked`).
        """
        res = self.session.get(f"{self.url}/ip")
        if res.status_code != 403:
            return None
        data = res.json()
        if not data.get("blocked"):
            return None
        return "query_only" if data.get("reason") == "ip_query_only" else "blocked"

    def get_country_code(self) -> Optional[str]:
        """Return the caller's country code as detected by the gateway, or None."""
        res = self.session.get(f"{self.url}/ip")
        return res.headers.get(COUNTRY_HEADER)

    def get_requires_cloudflare_auth(self) -> bool:
        """Return True if the client must complete the Cloudflare JS challenge."""
        res = self.session.get(f"{self.url}/cf-check")
        if res.status_code != 403:
            return False
        return res.headers.get("cf-mitigated") == "challenge"

    def get_time(self) -> int:
        """Return the gateway server time in epoch milliseconds."""
        res = self.session.get(f"{self.url}/time")
        return res.json()
