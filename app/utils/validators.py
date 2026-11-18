"""URL validation + SSRF protection."""
import asyncio
import ipaddress
import socket
from urllib.parse import urlparse


class URLValidationError(ValueError):
    pass


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def normalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        raise URLValidationError("URL is required.")
    if "://" not in raw:
        raw = "https://" + raw
    p = urlparse(raw)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise URLValidationError("Enter a valid http(s) URL.")
    if p.username or p.password:
        raise URLValidationError("URLs with credentials are not allowed.")
    if "." not in p.hostname and not _is_ip(p.hostname):
        raise URLValidationError("Enter a valid domain, e.g. example.com.")
    if p.port and p.port not in (80, 443, 8080, 8443):
        raise URLValidationError("Only standard web ports are allowed.")
    return raw


async def assert_public_host(host: str) -> None:
    """Resolve host and reject private/loopback/link-local/reserved addresses."""
    try:
        infos = await asyncio.to_thread(socket.getaddrinfo, host, None)
    except socket.gaierror:
        raise URLValidationError(f"Could not resolve host '{host}'.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if not ip.is_global:
            raise URLValidationError("Private or internal network addresses are not allowed.")
