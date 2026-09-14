"""Guard against ansible_managed inside ansible.builtin.copy content.

ansible_managed is injected into a template's own namespace by the
`template` action plugin; it is undefined for ordinary task-argument
templating such as `copy`'s `content:`. The existing template-rendering
tests in this suite cannot catch a misuse like that: they build their own
Jinja environment and hand it ansible_managed explicitly, which is a
namespace `copy` never has at runtime. This walks the actual task file
instead, so it fails the way the real playbook run does.
"""

import pathlib

import yaml

TASKS_FILE = (
    pathlib.Path(__file__).resolve().parents[2] / "roles/server/tasks/user.yml"
)

with open(TASKS_FILE, encoding="utf-8") as handle:
    TASKS = yaml.safe_load(handle)


def _copy_tasks(tasks):
    for task in tasks:
        args = task.get("ansible.builtin.copy")
        if isinstance(args, dict):
            yield task, args


def test_copy_content_never_references_ansible_managed():
    for task, args in _copy_tasks(TASKS):
        content = args.get("content") or ""
        assert "ansible_managed" not in content, (
            f"{task.get('name', '?')}: ansible_managed only resolves inside "
            "ansible.builtin.template, not ansible.builtin.copy's content -- "
            "hardcode the literal header instead"
        )
