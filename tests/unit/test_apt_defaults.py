"""The shipped defaults.

These are checked as data rather than through a play because the values are
Jinja strings the role resolves at run time; what matters here is the shape
and the naming convention, both of which a play would not fail loudly on.
"""

import pathlib
import re

import yaml

DEFAULTS = (
    pathlib.Path(__file__).resolve().parents[2] / "roles/server/defaults/main.yml"
)

MERGE_PATTERN = re.compile(r"^server_.+_apt_sources$")

with open(DEFAULTS, encoding="utf-8") as handle:
    SHIPPED = yaml.safe_load(handle)


def test_default_sources_follow_the_merge_convention():
    assert MERGE_PATTERN.match("server_default_apt_sources")
    assert "server_default_apt_sources" in SHIPPED


def test_merged_result_name_cannot_re_merge_into_itself():
    assert not MERGE_PATTERN.match("server_apt_sources")


def test_default_covers_release_updates_and_security():
    entries = SHIPPED["server_default_apt_sources"]
    assert [entry["name"] for entry in entries] == ["debian", "debian-security"]

    base, security = entries
    assert base["suites"] == [
        "{{ ansible_distribution_release }}",
        "{{ ansible_distribution_release }}-updates",
    ]
    assert security["suites"] == ["{{ ansible_distribution_release }}-security"]
    assert security["uris"] == "{{ server_apt_mirror }}-security"


def test_default_entries_carry_every_key_detect_requires():
    required = {"name", "uris", "suites", "components"}
    for entry in SHIPPED["server_default_apt_sources"]:
        missing = required - entry.keys()
        assert not missing, f"{entry.get('name', entry)} missing {missing}"


def test_default_entries_pin_the_debian_archive_keyring():
    # Scope each shipped entry to the Debian archive keyring specifically,
    # rather than letting it verify against every key in trusted.gpg.d.
    for entry in SHIPPED["server_default_apt_sources"]:
        assert entry.get("signed_by") == "/usr/share/keyrings/debian-archive-keyring.gpg"


def test_disable_list_defaults_to_empty():
    assert SHIPPED["server_apt_disable_sources"] == []


def test_superseded_variable_is_gone():
    assert "server_apt_repositories" not in SHIPPED
