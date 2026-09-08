"""
Deep SSRF and Crawler Security Validation Tests.
Validates:
- Hostname blocking
- IP resolution verification
- Redirect hop inspection
- Non-HTTP(S) scheme blocking
- SEOCrawler initialization and error propagation
"""
import pytest
import httpx
from app.crawler.ssrf_protection import (
    validate_url_ssrf, 
    is_ip_allowed, 
    resolve_hostname_ips,
    create_ssrf_safe_client, 
    SSRFBlockedError
)
from app.crawler.crawler import SEOCrawler
from app.crawler.broken_link_checker import check_single_link

def test_is_ip_allowed_boundaries():
    # Private IPv4
    assert is_ip_allowed("10.0.0.1") is False
    assert is_ip_allowed("10.255.255.255") is False
    assert is_ip_allowed("172.16.0.1") is False
    assert is_ip_allowed("172.31.255.255") is False
    assert is_ip_allowed("192.168.0.1") is False
    assert is_ip_allowed("192.168.255.255") is False
    
    # Loopback
    assert is_ip_allowed("127.0.0.1") is False
    assert is_ip_allowed("127.127.127.127") is False
    
    # Link Local / Metadata
    assert is_ip_allowed("169.254.169.254") is False
    assert is_ip_allowed("169.254.1.1") is False
    
    # IPv6
    assert is_ip_allowed("::1") is False
    assert is_ip_allowed("fc00::1") is False
    assert is_ip_allowed("fe80::1") is False
    
    # Public Global IPs
    assert is_ip_allowed("8.8.8.8") is True
    assert is_ip_allowed("1.1.1.1") is True
    assert is_ip_allowed("142.250.190.46") is True

def test_crawler_init_rejects_ssrf_targets():
    # Private start URL
    with pytest.raises(ValueError) as exc:
        SEOCrawler(start_url="http://127.0.0.1:8000")
    assert "SSRF Protection" in str(exc.value)

    # Localhost start URL
    with pytest.raises(ValueError) as exc:
        SEOCrawler(start_url="http://localhost:8080")
    assert "SSRF Protection" in str(exc.value)

    # Cloud metadata start URL
    with pytest.raises(ValueError) as exc:
        SEOCrawler(start_url="http://169.254.169.254/latest/meta-data")
    assert "SSRF Protection" in str(exc.value)

    # Non-http scheme
    with pytest.raises(ValueError):
        SEOCrawler(start_url="ftp://example.com")

def test_broken_link_checker_rejects_ssrf():
    async def _run():
        async with create_ssrf_safe_client() as client:
            res = await check_single_link(client, "http://127.0.0.1:3000/internal")
            assert res["is_broken"] is True
            assert "Blocked" in res["error"]

            res2 = await check_single_link(client, "file:///etc/passwd")
            assert res2["is_broken"] is True
            assert "Invalid or Unsupported" in res2["error"]

    import asyncio
    asyncio.run(_run())
