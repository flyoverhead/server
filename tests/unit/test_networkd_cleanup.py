"""The networkd cleanup must keep exactly the files the create tasks write.

It used to read `dest` from the registered template results, which check mode
omits for changed files, so every `--check` planned to delete them.
"""

import pathlib

import pytest
import yaml
from ansible.plugins.filter.core import FilterModule
from jinja2 import Environment, StrictUndefined

TASKS = pathlib.Path(__file__).resolve().parents[2] / "roles/systemd/tasks/config.yml"

ENV = Environment(undefined=StrictUndefined)
ENV.filters.update(
    {
        name: f
        for name, f in FilterModule().filters().items()
        if name not in ("default", "d")
    }
)


def _block(tasks, name):
    for task in tasks:
        if task.get("name") == name:
            return task
    raise AssertionError(name)


NETWORKD = _block(yaml.safe_load(TASKS.read_text()), "config | networkd")["block"]
CREATE = _block(NETWORKD, "config | create networkd")["block"]
USED = _block(_block(NETWORKD, "config | clean networkd")["block"], "config | set used networkd configurations")

ITEMS = [
    {"name": "lo", "kind": "loopback", "priority": 10},
    {"name": "eth0", "kind": "ether", "priority": 10},
    {"name": "eth1", "kind": "link", "priority": 10},
    {"name": "br0", "kind": "bridge", "priority": 20, "slaves": ["eth2"]},
    {"name": "bond0", "kind": "bond", "priority": 20},
    {"name": "vlan10", "kind": "vlan", "priority": 30},
    {"name": "tun0", "kind": "ipip", "priority": 40},
]


def _render(expression, **context):
    return ENV.from_string(expression).render(**context)


def _expected(item):
    paths = []
    for task in CREATE:
        if all(_render("{{ " + cond + " }}", item=item) == "True" for cond in task["when"]):
            paths.append(_render(task["ansible.builtin.template"]["dest"], item=item))
    return sorted(paths)


@pytest.mark.parametrize("item", ITEMS, ids=[i["name"] for i in ITEMS])
def test_used_paths_match_created_paths(item):
    path = _render(USED["vars"]["systemd_networkd_path"], item=item)
    expression = USED["ansible.builtin.set_fact"]["systemd_networkd_managed_devices"]
    rendered = _render(
        expression, item=item, systemd_networkd_path=path, systemd_networkd_managed_devices=[]
    )
    assert sorted(yaml.safe_load(rendered)) == _expected(item)
    assert _expected(item)


def test_cleanup_does_not_depend_on_registered_results():
    for task in CREATE:
        assert "register" not in task, task["name"]
    assert "results" not in yaml.safe_dump(USED)
