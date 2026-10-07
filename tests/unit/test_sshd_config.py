"""sshd keeps the distribution config and layers the role's settings on top."""

import pathlib

import yaml
from jinja2 import Environment, StrictUndefined

ROLE = pathlib.Path(__file__).resolve().parents[2] / "roles/server"
DROPIN = "/etc/ssh/sshd_config.d/00-server.conf"


def _load(relative):
    with open(ROLE / relative, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _walk(tasks):
    for task in tasks or []:
        yield task
        for key in ("block", "rescue", "always"):
            yield from _walk(task.get(key))


def _writers(tasks, dest):
    found = []
    for task in _walk(tasks):
        for module in ("ansible.builtin.template", "ansible.builtin.copy", "ansible.builtin.lineinfile"):
            args = task.get(module) or {}
            if args.get("dest") == dest or args.get("path") == dest:
                found.append(task)
    return found


TASK_FILES = sorted(p.relative_to(ROLE).as_posix() for p in (ROLE / "tasks").glob("*.yml"))
SSHD = _load("tasks/sshd.yml")


def _render_dropin(port):
    env = Environment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)
    env.filters["comment"] = lambda text: "#\n# " + text + "\n#"
    source = (ROLE / "templates/sshd_server.conf.j2").read_text(encoding="utf-8")
    return env.from_string(source).render(ansible_managed="Ansible managed", server_ssh_port=port)


def _directives(text):
    pairs = {}
    for line in text.splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            key, value = line.split(None, 1)
            pairs[key] = value
    return pairs


def test_only_sshd_yml_writes_the_main_config():
    for relative in TASK_FILES:
        writers = _writers(_load(relative), "/etc/ssh/sshd_config")
        if relative == "tasks/sshd.yml":
            assert len(writers) == 1
        else:
            assert writers == [], relative


def test_main_config_is_the_packaged_stock_file():
    (task,) = _writers(SSHD, "/etc/ssh/sshd_config")
    args = task["ansible.builtin.copy"]
    assert args["src"] == "/usr/share/openssh/sshd_config"
    assert args["remote_src"] is True
    assert args["validate"] == "/usr/sbin/sshd -t -f %s"


def test_dropin_is_validated_and_written_before_the_stock_file():
    names = [task["name"] for task in SSHD]
    (dropin,) = _writers(SSHD, DROPIN)
    (stock,) = _writers(SSHD, "/etc/ssh/sshd_config")
    assert dropin["ansible.builtin.template"]["validate"] == "/usr/sbin/sshd -t -f %s"
    assert names.index(dropin["name"]) < names.index(stock["name"])


def test_dropin_sorts_before_cloud_init():
    assert pathlib.PurePath(DROPIN).name < "50-cloud-init.conf"


def test_dropin_directives():
    assert _directives(_render_dropin(33731)) == {
        "Port": "33731",
        "PermitRootLogin": "no",
        "PubkeyAuthentication": "yes",
        "PasswordAuthentication": "no",
        "KbdInteractiveAuthentication": "no",
    }


def test_every_sshd_write_restarts_ssh():
    for task in SSHD:
        assert task.get("notify") == ["ssh | restart service"], task["name"]


def test_sshd_runs_before_the_port_move():
    names = [task["name"] for task in _load("tasks/main.yml")]
    assert names.index("sshd") < names.index("ssh")
