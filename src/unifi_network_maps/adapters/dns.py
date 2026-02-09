"""Reverse DNS hostname resolution."""

from __future__ import annotations

import logging

import dns.resolver
import dns.reversename

logger = logging.getLogger(__name__)


def resolve_hostnames(
    ips: list[str],
    dns_server: str,
    timeout: float = 2.0,
) -> dict[str, str]:
    """Reverse-resolve IPs to hostnames using a specific DNS server.

    Uses dnspython to query the given dns_server for PTR records.
    Returns {ip: hostname} for successful resolutions only.
    Failures are silently skipped (logged at debug level).
    """
    resolver = dns.resolver.Resolver(configure=False)
    try:
        resolver.nameservers = [dns_server]
    except ValueError:
        logger.debug("Invalid DNS server address: %s", dns_server)
        return {}
    resolver.lifetime = timeout

    results: dict[str, str] = {}
    for ip in ips:
        try:
            rev_name = dns.reversename.from_address(ip)
            answer = resolver.resolve(rev_name, "PTR")
            hostname = str(answer[0]).rstrip(".")
            results[ip] = hostname
        except Exception:  # noqa: BLE001
            logger.debug("Reverse DNS lookup failed for %s", ip)
    return results
