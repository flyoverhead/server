"""The ssh port probes, asserted as data."""

import pathlib

import yaml

ROLE = pathlib.Path(__file__).resolve().parents[2] / "roles/server"


def _load(relative):
    with open(ROLE / relative, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


DETECT = _load("tasks/detect.yml")
SSH = _load("tasks/ssh.yml")


def _walk(tasks):
    for task in tasks or []:
        yield task
        for key in ("block", "rescue", "always"):
            yield from _walk(task.get(key))


def _probes(tasks):
    return [task for task in _walk(tasks) if "ansible.builtin.wait_for" in task]


def _by_name(tasks, needle):
    for task in _walk(tasks):
        if needle in task.get("name", ""):
            return task
    raise AssertionError(f"no task whose name contains {needle!r}")


def test_every_port_probe_requires_an_ssh_banner():
    probes = _probes(DETECT) + _probes(SSH)
    assert len(probes) == 3
    for probe in probes:
        args = probe["ansible.builtin.wait_for"]
        assert args.get("search_regex") == "SSH-", probe.get("name", "?")


def test_the_custom_port_is_probed_before_the_default():
    names = [probe.get("name", "") for probe in _probes(DETECT)]
    assert "custom ssh port" in names[0]
    assert "default ssh port" in names[1]


def test_the_default_port_is_only_probed_when_the_custom_one_timed_out():
    task = _by_name(DETECT, "detect | default ssh port")
    assert "server_detect_custom_port.msg" in str(task["when"])


def test_the_downgrade_needs_the_custom_port_to_have_timed_out():
    task = _by_name(DETECT, "detect | default ssh port fact")
    when = str(task["when"])
    assert "server_detect_custom_port.msg" in when
    assert "server_default_ssh_port.msg" in when


def test_every_probe_runs_from_the_controller():
    for probe in _probes(DETECT) + _probes(SSH):
        assert probe["delegate_to"] == "localhost", probe.get("name", "?")
