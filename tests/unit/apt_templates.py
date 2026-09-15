"""Render roles/server templates with Ansible's real filters.

Deliberately not conftest.py, matching the convention in new_lab's
tests/keenetic/keenetic_templates.py: there is no __init__.py under tests/,
so a second conftest.py anywhere would collide on the module name.

trim_blocks and lstrip_blocks mirror what tasks/user.yml passes to the
template module, so what this renders is what the host gets.
"""

import pathlib

from ansible.plugins.filter.core import FilterModule
from jinja2 import Environment, FileSystemLoader, StrictUndefined

TEMPLATE_DIR = (
    pathlib.Path(__file__).resolve().parents[2] / "roles/server/templates"
)

ENV = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    undefined=StrictUndefined,
)
_ANSIBLE_FILTERS = {
    name: f
    for name, f in FilterModule().filters().items()
    if name not in ("default", "d")
}
ENV.filters.update(_ANSIBLE_FILTERS)

HEADER = "#\n# Ansible managed\n#\n"


def render(item):
    return ENV.get_template("apt.sources.j2").render(
        item=item, ansible_managed="Ansible managed"
    )
