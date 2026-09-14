"""The deb822 drop-in template.

Field order is fixed and asserted in full rather than by substring: apt does
not care about order, but a full-output assertion is what catches a field
silently vanishing when the template is edited.
"""

import pathlib

import pytest
from jinja2 import UndefinedError

from apt_templates import HEADER, TEMPLATE_DIR, render

MINIMAL = {
    "name": "debian",
    "uris": "http://mirror.yandex.ru/debian",
    "suites": "trixie",
    "components": "main",
}


def test_scalars_render_one_stanza():
    assert render(MINIMAL) == (
        HEADER + "\n"
        "Types: deb\n"
        "URIs: http://mirror.yandex.ru/debian\n"
        "Suites: trixie\n"
        "Components: main\n"
    )


def test_lists_join_on_spaces():
    out = render(
        dict(
            MINIMAL,
            suites=["trixie", "trixie-updates"],
            components=["main", "contrib", "non-free"],
        )
    )
    assert "Suites: trixie trixie-updates\n" in out
    assert "Components: main contrib non-free\n" in out


def test_uris_as_list():
    out = render(
        dict(
            MINIMAL,
            uris=["http://mirror.yandex.ru/debian", "http://mirror2.yandex.ru/debian"],
        )
    )
    assert "URIs: http://mirror.yandex.ru/debian http://mirror2.yandex.ru/debian\n" in out


def test_architectures_as_list():
    out = render(
        dict(
            MINIMAL,
            architectures=["arm64", "amd64"],
        )
    )
    assert "Architectures: arm64 amd64\n" in out


def test_signed_by_as_list():
    out = render(
        dict(
            MINIMAL,
            signed_by=["/usr/share/keyrings/debian-archive-keyring.gpg", "/usr/share/keyrings/armbian-archive-keyring.gpg"],
        )
    )
    assert "Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg /usr/share/keyrings/armbian-archive-keyring.gpg\n" in out


def test_optional_fields_are_omitted():
    out = render(MINIMAL)
    for absent in ("Architectures:", "Signed-By:", "Enabled:"):
        assert absent not in out


def test_optional_fields_render_when_given():
    out = render(
        dict(
            MINIMAL,
            types=["deb", "deb-src"],
            architectures="arm64",
            signed_by="/usr/share/keyrings/armbian-archive-keyring.gpg",
            enabled=True,
        )
    )
    assert "Types: deb deb-src\n" in out
    assert "Architectures: arm64\n" in out
    assert "Signed-By: /usr/share/keyrings/armbian-archive-keyring.gpg\n" in out
    assert "Enabled: yes\n" in out


def test_enabled_false_renders_no():
    assert "Enabled: no\n" in render(dict(MINIMAL, enabled=False))


@pytest.mark.parametrize("missing", ["uris", "suites", "components"])
def test_required_fields_are_not_silently_empty(missing):
    item = {k: v for k, v in MINIMAL.items() if k != missing}
    with pytest.raises(UndefinedError):
        render(item)


def test_superseded_draft_template_is_gone():
    assert not (TEMPLATE_DIR / "repository.sources.j2").exists()
