import pytest
import ipaddress
from app.crawler.ssrf_protection import (
    validate_url_ssrf,
    is_ip_allowed,
    resolve_hostname_ips,
    SSRFBlockedError
)
from app.config.utils import get_project_storage_dir, get_project_storage_key


class TestSSRFProtection:
    """
    Automated SSRF security suite testing IP parsing, fail-closed DNS resolution,
    private/loopback/link-local/metadata blocking, and IPv4-mapped IPv6 representations.
    """

    def test_public_ips_allowed(self):
        assert is_ip_allowed("93.184.216.34") is True
        assert is_ip_allowed("8.8.8.8") is True
        assert is_ip_allowed("2606:4700:4700::1111") is True

    def test_loopback_and_private_ipv4_blocked(self):
        assert is_ip_allowed("127.0.0.1") is False
        assert is_ip_allowed("127.0.0.2") is False
        assert is_ip_allowed("10.0.0.1") is False
        assert is_ip_allowed("172.16.0.1") is False
        assert is_ip_allowed("192.168.1.1") is False

    def test_cloud_metadata_and_link_local_blocked(self):
        assert is_ip_allowed("169.254.169.254") is False
        assert is_ip_allowed("169.254.0.1") is False

    def test_ipv6_loopback_and_private_blocked(self):
        assert is_ip_allowed("::1") is False
        assert is_ip_allowed("fe80::1") is False
        assert is_ip_allowed("fc00::1") is False

    def test_ipv4_mapped_ipv6_blocked(self):
        # ::ffff:127.0.0.1 and ::ffff:169.254.169.254 must be blocked
        assert is_ip_allowed("::ffff:127.0.0.1") is False
        assert is_ip_allowed("::ffff:10.0.0.1") is False
        assert is_ip_allowed("::ffff:169.254.169.254") is False

    def test_decimal_and_hex_ip_integers_blocked(self):
        # 2130706433 is decimal representation of 127.0.0.1
        assert is_ip_allowed("2130706433") is False
        assert is_ip_allowed("0x7f000001") is False

    def test_validate_url_ssrf_blocked_hostnames(self):
        valid, reason = validate_url_ssrf("http://localhost/admin")
        assert valid is False
        assert "blocked" in reason.lower()

        valid, reason = validate_url_ssrf("http://127.0.0.1:8080/metrics")
        assert valid is False

        valid, reason = validate_url_ssrf("http://169.254.169.254/latest/meta-data/")
        assert valid is False

    def test_validate_url_ssrf_fail_closed_on_unresolvable_dns(self):
        # Unresolvable fake domain must fail-closed in strict mode
        valid, reason = validate_url_ssrf("http://nonexistent-fake-domain-123456789.invalid/")
        assert valid is False
        assert "could not be resolved" in reason.lower()

    def test_top10_valid_domain_not_false_positive_blocked(self):
        # Domains containing "10." (e.g. top10.com) should not be blocked by substring checks
        valid, reason = validate_url_ssrf("https://top10.com/")
        if not valid:
            assert "references blocked IP" not in reason


class TestProjectDataIsolation:
    """
    Automated test suite verifying multi-tenant project directory isolation.
    """

    def test_storage_dir_isolation_for_same_domain(self):
        base_dir = "/tmp/crawl_test_dir"
        dir_proj1 = get_project_storage_dir(base_dir, "example.com", "proj_aaa")
        dir_proj2 = get_project_storage_dir(base_dir, "example.com", "proj_bbb")

        assert dir_proj1 != dir_proj2
        assert "proj_aaa" in dir_proj1
        assert "proj_bbb" in dir_proj2
