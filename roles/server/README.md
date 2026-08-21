# `flyoverhead.server.server`

Base Debian server configuration: the login user, sudo, authorized keys, the
sshd port, apt sources, hostname, timezone, base packages and an optional
full upgrade.

## Role variables

| Variable | Description | Example |
| :--- | :--- | :--- |
| `server_user` | Login user to create: `name`, `group`, `home`, `password`, `authorized_ssh_keys` | Definition example in [defaults/main.yml](defaults/main.yml) |
| `server_root_password` | Root password. `'*'` locks the account, an empty string skips the task | `'*'` |
| `server_apt_mirror` | Base URL written into `/etc/apt/sources.list` | `http://deb.debian.org/debian` |
| `server_apt_components` | Components appended to every apt line | `[main, contrib]` |
| `server_packages` | Packages installed on every host | Definition example in [defaults/main.yml](defaults/main.yml) |
| `server_pip_pyenv_path` | Virtualenv the pip packages go into | `/home/user/.venv` |
| `server_pip_packages` | Packages installed into that virtualenv | `[pip]` |
| `server_timezone` | System timezone | `Europe/Moscow` |
| `server_upgrade` | Run `apt upgrade`, autoremove and a `needrestart` check | `false` |

`server_user.authorized_ssh_keys` names public keys under `~/.ssh` **on the
controller**, without the `.pub` suffix — [tasks/user.yml](tasks/user.yml)
appends it. `id_ed25519` reads `~/.ssh/id_ed25519.pub`.

### Variables the caller must supply

These two are deliberately unprefixed, because the `rocky` role outside this
collection reads the same names:

| Variable | Description |
| :--- | :--- |
| `default_user` | Stock user of the untouched image, used to bootstrap a host that rejects `ansible_user` |
| `default_password` | That user's password |

They are only consulted when the first connection attempt fails with
`Permission denied`, i.e. on the first run against a freshly-provisioned host.
Once `server_user` exists they are unused.

## Facts set by this role

| Fact | Description |
| :--- | :--- |
| `server_ssh_port` | Target sshd port, taken from `ansible_port` |
| `server_ssh_host` | Address the port checks are made against |
| `server_check_connection_result` | Result of the initial `ping`, used to pick the bootstrap credentials |
| `server_ssh_socket_config` | Whether sshd is socket-activated and needs an `ssh.socket` drop-in |
| `ansible_port` | Rewritten to 22 while bootstrapping, then to `server_ssh_port` once sshd has moved |
| `ansible_user`, `ansible_password` | Rewritten to `server_user` once it exists |

## Tags

`server.user`, `server.ssh`, `server.config`, `server.host`, `server.root`,
`server.timezone`, `server.packages`, `server.pip`, `server.upgrade`.

The detection block carries all of them, so any single tag still runs the
fact-gathering it depends on.

## Behaviour worth knowing before the first run

- **`ansible_port` must not be 22.** `server_ssh_port` is only set when
  `ansible_port != 22`, and [tasks/main.yml](tasks/main.yml) gates the sshd move
  on `server_ssh_port != ansible_port`. Set `ansible_port` to the port you want
  sshd to end up on; the role finds the host on 22 and moves it there.
- **`/etc/ssh/sshd_config` is replaced wholesale** by
  [templates/sshd_config.j2](templates/sshd_config.j2), which sets only `Port`,
  `PermitRootLogin no` and `PubkeyAuthentication yes`. Every other directive in
  the distribution file is dropped. Note it does not disable password
  authentication.
- **`/etc/apt/sources.list` is replaced** with three one-line entries built from
  `server_apt_mirror`. Any `sources.list.d` snippet is left alone.
- The root password is hashed with a salt seeded from `inventory_hostname`, so
  it is stable across runs. `server_user.password` is hashed **without** a seed,
  so `user | create` reports `changed` on every run even when nothing differs.

## Example playbook

```yaml
- hosts: server
  gather_facts: true
  vars:
    ansible_port: 33731
    default_user: root
    default_password: '{{ vault_image_root_password }}'
  roles:
    - role: flyoverhead.server.server
```
