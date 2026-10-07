"""The auto-added default interface keeps the host's real prefix length."""

import ast
import pathlib

import pytest
import yaml
from jinja2 import Environment, StrictUndefined

TASKS = pathlib.Path(__file__).resolve().parents[2] / "roles/systemd/tasks/detect.yml"


def _task(tasks, name):
    for task in tasks:
        if task.get("name") == name:
            return task
        found = task.get("block") and _task(task["block"], name)
        if found:
            return found
    return None


ADD = _task(yaml.safe_load(TASKS.read_text()), "detect | add default interface")


@pytest.mark.parametrize("prefix", ["32", "24", "22"])
def test_address_carries_the_fact_prefix(prefix):
    expression = ADD["ansible.builtin.set_fact"]["systemd_networkd"]
    rendered = Environment(undefined=StrictUndefined).from_string(expression).render(
        systemd_networkd=[],
        ansible_default_ipv4={
            "interface": "eth0",
            "type": "ether",
            "address": "192.0.2.10",
            "prefix": prefix,
            "gateway": "192.0.2.1",
        },
        systemd_resolved={"dns": [], "domains": []},
    )
    (item,) = ast.literal_eval(rendered.strip())
    assert item["address"] == f"192.0.2.10/{prefix}"
