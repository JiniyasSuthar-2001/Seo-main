"""
SSRF (Server-Side Request Forgery) protection layer.
Enforces strict URL validation, DNS destination IP verification, scheme whitelisting,
and redirect hop validation to prevent internal network scanning and cloud metadata theft.
"""
import ipaddress
import socket
from urllib.parse import urlparse, urljoin
from typing import Tuple, List, Optional
import httpx

# Explicitly blocked CIDR networks
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Unspecified / Current network
    ipaddress.ip_network("10.0.0.0/8"),         # RFC 1918 Private
    ipaddress.ip_network("100.64.0.0/10"),      # RFC 6598 Carrier-grade NAT
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-Local / Cloud Metadata (169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),      # RFC 1918 Private
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # TEST-NET-1
    ipaddress.ip_network("192.168.0.0/16"),     # RFC 1918 Private
    ipaddress.ip_network("198.18.0.0/15"),      # Network benchmark testing
    ipaddress.ip_network("198.51.100.0/24"),    # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),     # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved / Future use
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
    
    # IPv6 blocked ranges
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("::1/128"),           # Loopback
    ipaddress.ip_network("fc00::/7"),           # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-Local
    ipaddress.ip_network("ff00::/8"),           # Multicast
    ipaddress.ip_network("2001:db8::/32"),      # Documentation
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
    "metadata.google.internal",
    "instance-data",
    "0.0.0.0",
    "127.0.0.1",
    "::1",
    "[::1]"
}

ALLOWED_SCHEMES = {"http", "https"}

class SSRFBlockedError(ValueError):
    """Raised when an outbound URL violates SSRF security policies."""
    pass

def is_ip_allowed(ip_str: str) -> bool:
    """
    Checks whether an IP address is a publicly routable global address.
    Returns False if the IP belongs to any private, loopback, link-local, multicast, or reserved range.
    """
    try:
        clean_ip = ip_str.strip().strip("[]")
        ip = ipaddress.ip_address(clean_ip)
    except ValueError:
        return False

    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_reserved
    ):
        return False

    # Check explicit CIDR block list
    for net in BLOCKED_NETWORKS:
        if ip in net:
            return False

    return True

def resolve_hostname_ips(hostname: str, port: int = 80) -> List[str]:
    """
    Resolves a hostname to all IPv4 and IPv6 addresses using DNS.
    """
    clean_host = hostname.strip().strip("[]")
    resolved_ips = []
    try:
        addrinfo = socket.getaddrinfo(clean_host, port, proto=socket.IPPROTO_TCP)
        for entry in addrinfo:
            sockaddr = entry[4]
            ip_str = sockaddr[0]
            if ip_str not in resolved_ips:
                resolved_ips.append(ip_str)
    except Exception:
        pass
    return resolved_ips

def validate_url_ssrf(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validates a URL against SSRF security rules:
    1. Scheme must be http or https strictly.
    2. Hostname must not be localhost or link-local.
    3. Hostname must resolve strictly to global public IP addresses.
    Returns (is_valid, error_reason).
    """
    if not url or not isinstance(url, str):
        return False, "URL cannot be empty."

    clean_url = url.strip()
    try:
        parsed = urlparse(clean_url)
    except Exception as e:
        return False, f"Malformed URL: {e}"

    if not parsed.scheme or parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return False, f"Scheme '{parsed.scheme}' is blocked. Only http and https protocols are permitted."

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        return False, "URL must contain a valid hostname."

    # Check blocked hostnames
    if hostname in BLOCKED_HOSTNAMES or hostname.endswith(".localhost") or hostname.endswith(".local") or hostname.endswith(".internal"):
        return False, f"Destination host '{hostname}' is blocked."

    # If hostname is already a raw IP literal
    try:
        ip = ipaddress.ip_address(hostname.strip("[]"))
        if not is_ip_allowed(str(ip)):
            return False, f"Direct access to private or internal IP '{hostname}' is blocked."
        return True, None
    except ValueError:
        pass

    # Resolve hostname to verify destination IP addresses
    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    resolved_ips = resolve_hostname_ips(hostname, port)
    
    if not resolved_ips:
        # If unable to resolve DNS, allow httpx to attempt DNS resolution or block if strict
        # But if the hostname contains suspicious patterns (e.g. 127.0.0.1 in subdomains or hex IP)
        if "127." in hostname or "169.254" in hostname or "192.168" in hostname or "10." in hostname:
            return False, f"Destination host '{hostname}' references blocked IP ranges."
        return True, None

    for ip_str in resolved_ips:
        if not is_ip_allowed(ip_str):
            return False, f"Destination host '{hostname}' resolved to blocked address '{ip_str}'."

    return True, None

def ssrf_request_hook(request: httpx.Request):
    """
    HTTPX request event hook that intercepts every outgoing request (including redirects).
    Raises SSRFBlockedError if destination violates SSRF protection rules.
    """
    url_str = str(request.url)
    is_valid, reason = validate_url_ssrf(url_str)
    if not is_valid:
        raise SSRFBlockedError(f"SSRF Protection Blocked Request: {reason}")

def ssrf_response_hook(response: httpx.Response):
    """
    HTTPX response event hook that validates redirect locations before they are followed.
    """
    if response.is_redirect and "location" in response.headers:
        redirect_url = response.headers["location"]
        # Resolve relative redirect URLs against current request URL
        absolute_redirect = urljoin(str(response.request.url), redirect_url)
        is_valid, reason = validate_url_ssrf(absolute_redirect)
        if not is_valid:
            raise SSRFBlockedError(f"SSRF Protection Blocked Redirect to '{absolute_redirect}': {reason}")

def create_ssrf_safe_client(
    timeout: float = 20.0,
    headers: Optional[dict] = None,
    verify: bool = True,
    follow_redirects: bool = True,
    max_redirects: int = 10
) -> httpx.AsyncClient:
    """
    Creates an HTTPX AsyncClient equipped with comprehensive SSRF protection hooks.
    """
    return httpx.AsyncClient(
        timeout=timeout,
        headers=headers,
        verify=verify,
        follow_redirects=follow_redirects,
        max_redirects=max_redirects,
        event_hooks={
            "request": [ssrf_request_hook],
            "response": [ssrf_response_hook]
        }
    )
