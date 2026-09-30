"""resolved.conf and networkd DNS options: absent keys must render nothing."""

import pathlib

import pytest
from ansible.plugins.filter.core import FilterModule
from jinja2 import Environment, FileSystemLoader, StrictUndefined

TEMPLATE_DIR = (
    pathlib.Path(__file__).resolve().parents[2] / "roles/systemd/templates"
)

ENV = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    undefined=StrictUndefined,
)
ENV.filters.update(
    {
        name: f
        for name, f in FilterModule().filters().items()
        if name not in ("default", "d")
    }
)

BASE = {"dns": ["9.9.9.9"], "domains": [], "cache": True, "stub_listener": True}


def resolved(**extra):
    return ENV.get_template("resolved.conf.j2").render(
        systemd_resolved=dict(BASE, **extra), ansible_managed="Ansible managed"
    )


def network(**extra):
    item = dict(
        {"name": "eth0", "kind": "ether", "address": "192.0.2.10/24"}, **extra
    )
    return ENV.get_template("networkd.network.j2").render(
        item=item, ansible_managed="Ansible managed"
    )


def test_resolved_unchanged_without_new_keys():
    out = resolved()
    assert "DNSOverTLS" not in out
    assert "FallbackDNS" not in out
    assert "DNS=9.9.9.9\n" in out


@pytest.mark.parametrize(
    "value, expected",
    [(True, "yes"), (False, "no"), ("opportunistic", "opportunistic")],
)
def test_resolved_dns_over_tls(value, expected):
    assert f"\nDNSOverTLS={expected}\n" in resolved(dns_over_tls=value)


def test_resolved_dns_keeps_server_name():
    out = resolved(dns=["1.1.1.1#cloudflare-dns.com", "77.88.8.8#common.dot.dns.yandex.net"])
    assert "\nDNS=1.1.1.1#cloudflare-dns.com 77.88.8.8#common.dot.dns.yandex.net\n" in out


def test_resolved_empty_fallback_disables_builtin_list():
    assert "\nFallbackDNS=\n" in resolved(fallback_dns=[])


def test_resolved_fallback_joined():
    assert "\nFallbackDNS=1.1.1.1 9.9.9.9\n" in resolved(
        fallback_dns=["1.1.1.1", "9.9.9.9"]
    )


def test_network_without_dns_default_route():
    assert "DNSDefaultRoute" not in network()


@pytest.mark.parametrize("value, expected", [(False, "no"), (True, "yes")])
def test_network_dns_default_route(value, expected):
    assert f"\nDNSDefaultRoute={expected}\n" in network(dns_default_route=value)
