"""The uv tasks and defaults, asserted as data."""

import pathlib
import re

import yaml

ROLE = pathlib.Path(__file__).resolve().parents[2] / "roles/server"


def _load(relative):
    with open(ROLE / relative, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


PACKAGES = _load("tasks/packages.yml")
UV = _load("tasks/uv.yml")
MAIN = _load("tasks/main.yml")
DEFAULTS = _load("defaults/main.yml")


def _by_name(tasks, needle):
    for task in tasks:
        if needle in task.get("name", ""):
            return task
    raise AssertionError(f"no task whose name contains {needle!r}")


def test_no_task_still_uses_the_pip_module():
    for task in PACKAGES + UV:
        assert "ansible.builtin.pip" not in task, task.get("name", "?")


def test_venv_creation_is_guarded_against_wiping_the_venv():
    task = _by_name(PACKAGES, "create virtualenv")
    creates = task["ansible.builtin.command"]["creates"]
    assert creates == "{{ server_pip_pyenv_path }}/bin/python"


def test_venv_never_downloads_its_own_python():
    task = _by_name(PACKAGES, "create virtualenv")
    assert "--no-python-downloads" in task["ansible.builtin.command"]["cmd"]


def test_install_reports_change_from_stderr_not_stdout():
    task = _by_name(PACKAGES, "install pip packages")
    assert "stderr" in task["changed_when"]
    assert "stdout" not in task["changed_when"]
    assert "Installed" in task["changed_when"]


def test_install_is_skipped_when_no_packages_are_requested():
    task = _by_name(PACKAGES, "install pip packages")
    assert "server_pip_packages | length > 0" in str(task["when"])


def test_uv_install_is_version_pinned_and_arch_mapped():
    assert re.fullmatch(r"\d+\.\d+\.\d+", str(DEFAULTS["server_uv_version"]))
    assert set(DEFAULTS["server_uv_arch"]) >= {"x86_64", "aarch64"}
    assert "{{ server_uv_version }}" in DEFAULTS["server_uv_url"]
    assert "server_uv_arch[ansible_architecture]" in DEFAULTS["server_uv_url"]


def test_uv_install_reruns_when_the_pinned_version_changes():
    task = _by_name(UV, "uv | install")
    when = str(task["when"])
    assert "server_uv_version !=" in when
    assert "split" in when


def test_uv_install_guard_is_not_a_bare_substring_test():
    task = _by_name(UV, "uv | install")
    when = str(task["when"])
    assert " not in " not in when
    assert " in " not in when


def test_uv_comes_from_server_uv_bin_not_the_bare_path():
    for task in PACKAGES + UV:
        cmd = str(task.get("ansible.builtin.command", {}).get("cmd", ""))
        if not cmd:
            continue
        assert not re.match(r"^uv(\s|$)", cmd.strip())
        assert "{{ server_uv_bin }}" in cmd

    dest = _by_name(UV, "uv | install")["ansible.builtin.unarchive"]["dest"]
    assert dest == "{{ server_uv_bin | dirname }}"
    assert DEFAULTS["server_uv_bin"] == "/usr/local/bin/uv"


def test_uv_include_runs_under_the_pip_tag_too():
    task = _by_name(MAIN, "uv")
    assert {"server.pip", "server.uv"} <= set(task["tags"])
    apply_tags = task["ansible.builtin.include_tasks"]["apply"]["tags"]
    assert {"server.pip", "server.packages"} <= set(apply_tags)


def test_detect_include_selects_uv_under_both_tag_lists():
    task = _by_name(MAIN, "detect")
    assert "server.uv" in task["tags"]
    apply_tags = task["ansible.builtin.include_tasks"]["apply"]["tags"]
    assert "server.uv" in apply_tags


def test_python3_pip_is_gone_from_the_package_list():
    assert "python3-pip" not in DEFAULTS["server_packages"]
    assert "python3" in DEFAULTS["server_packages"]
    assert "python3-dev" in DEFAULTS["server_packages"]


def test_pip_is_no_longer_a_default_package():
    assert DEFAULTS["server_pip_packages"] == []
