# `flyoverhead.server`

[![Version](https://img.shields.io/badge/version-2.0.0-blue)](galaxy.yml)
[![ansible-core](https://img.shields.io/badge/ansible--core-%E2%89%A52.16-black?logo=ansible&logoColor=white)](https://docs.ansible.com/ansible-core/devel/index.html)
[![License](https://img.shields.io/badge/license-GPL--3.0--only-green)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform](https://img.shields.io/badge/platform-Debian%2012%20%7C%2013-A81D33?logo=debian&logoColor=white)](#-supported-os)
[![Roles](https://img.shields.io/badge/roles-4-orange)](#-roles)

Remote server configuration: the base Debian setup, systemd networking and
firewalling, a zsh login shell and fail2ban.

These roles configure a machine you already have. Provisioning it — creating
the VPS at a provider — is out of scope.

## 🚀 Quick Start

### Requirements

- `ansible-core >=2.16`

- Collections: `ansible.posix >=1.5.4`, `community.general >=8.0.0`

- `jmespath` on the controller (the `systemd` role uses the `json_query` filter)

- Task `>=3.20`, Vagrant and a VMware Fusion provider, for the test harness only

### Installation

Installing the collection dependencies:

```bash
ansible-galaxy collection install -r requirements.yml
pip install -r requirements.txt
```

Installing the collection itself:

```bash
ansible-galaxy collection install git+https://github.com/flyoverhead/server.git
```

### Roles usage

Full documentation and usage examples of role `<role>` can be found in
`roles/<role>/README.md`.

Run `flyoverhead.server.server` first, on every host. It creates the login user
and sudo rights the later roles connect with, and settles the sshd port that
`systemd` opens in firewalld and `fail2ban` watches. Then `systemd`, because
`fail2ban` bans through firewalld rich rules and cannot start without it.
`ohmyzsh` is independent and can go anywhere.

### Example Playbook

```yaml
---
- hosts: all
  gather_facts: true
  vars:
    ansible_port: 33731
    default_user: root
    default_password: '{{ vault_image_root_password }}'
  roles:
    - flyoverhead.server.server
    - flyoverhead.server.systemd
    - flyoverhead.server.ohmyzsh
    - flyoverhead.server.fail2ban
```

`ansible_port` must not be 22. The `server` role finds the host on 22 and moves
sshd to `ansible_port`; see [roles/server/README.md](roles/server/README.md).

Two variables are deliberately unprefixed — `default_user` and
`default_password` — because a sibling role outside this collection reads the
same names. They are the stock credentials of the untouched image, used only to
bootstrap the first run.

## 🖥 Supported OS

| OS | Status |
| :--- | :--- |
| Debian 12 "Bookworm" (AArch64, x86_64) | Tested |
| Debian 13 "Trixie" | Supported, untested |

Everything is apt-based and Debian-family only. The `systemd` role installs
`libnss-resolve` instead of `systemd-resolved` below Debian 12, but nothing
older is tested.

## 📦 Roles

| Name | Description |
| :--- | :--- |
| [`server`](roles/server/README.md) | Login user, sudo, authorized keys, sshd port, apt sources, hostname, timezone, base packages |
| [`systemd`](roles/systemd/README.md) | firewalld on nftables, systemd-networkd, systemd-resolved, systemd-timesyncd |
| [`ohmyzsh`](roles/ohmyzsh/README.md) | Oh My Zsh, powerlevel10k, plugins, MesloLGS NF fonts |
| [`fail2ban`](roles/fail2ban/README.md) | fail2ban with an `[sshd]` jail and optional Telegram notifications |

## ⚠️ Gotchas

Three things here rewrite state rather than adding to it. All are documented per
role, collected once here:

- **`server` replaces `/etc/ssh/sshd_config` wholesale** with three directives
  (`Port`, `PermitRootLogin no`, `PubkeyAuthentication yes`). Every other
  directive in the distribution file is dropped, and password authentication is
  *not* disabled.
- **`server` empties `/etc/apt/sources.list`** to a comment and writes every
  repository as a deb822 drop-in under `sources.list.d`, one file per merged
  `server_*_apt_sources` entry. An entry overwrites an image-shipped file of
  the same name; anything not named by an entry or by
  `server_apt_disable_sources` is left alone.
- **`systemd` with a non-empty `systemd_networkd` takes networking over.** It
  deletes every file under `/etc/systemd/network` it did not just write,
  overwrites `/etc/network/interfaces`, masks the legacy `networking` service
  and queues a reboot. The default is `[]`, which skips all of it.

## 🧪 Testing

```bash
task deploy      # vagrant up, then run tests/playbook.yml against it
task provision   # re-run the playbook
task destroy
```

The harness leaves sshd on port 22 so `vagrant ssh` keeps working, which means
**the sshd port migration in `server/tasks/ssh.yml` is the one path it does not
cover** — exercising it needs a host whose port you are willing to move out
from under the provider. `tests/group_vars/systemd.yml` likewise ships
`systemd_networkd: []`, with the networkd definition commented out, for the
reason given in that file.

## 📄 License

GPL-3.0-only, except the `fail2ban` role, which began as a fork of
[`robertdebock.fail2ban`](https://github.com/robertdebock/ansible-role-fail2ban)
and keeps its original Apache-2.0 licence.
