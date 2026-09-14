# `flyoverhead.server.server`

Base Debian server configuration: the login user, sudo, authorized keys, the
sshd port, apt sources, hostname, timezone, base packages and an optional
full upgrade.

## Role variables

| Variable | Description | Example |
| :--- | :--- | :--- |
| `server_user` | Login user to create: `name`, `group`, `home`, `password`, `authorized_ssh_keys` | Definition example in [defaults/main.yml](defaults/main.yml) |
| `server_root_password` | Root password. `'*'` locks the account, an empty string skips the task | `'*'` |
| `server_apt_mirror` | Base URL the shipped Debian default builds its entries from | `http://deb.debian.org/debian` |
| `server_apt_components` | Components the shipped Debian default puts on every entry | `[main, contrib]` |
| `server_*_apt_sources` | Repositories, merged across every variable matching `^server_.+_apt_sources$` | Definition example in [defaults/main.yml](defaults/main.yml) |
| `server_apt_disable_sources` | Filenames under `sources.list.d` to neutralise | `[armbian.list]` |
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
- **`/etc/apt/sources.list` is emptied to a comment.** Every repository is a
  deb822 file under `sources.list.d`, one per merged entry, named
  `<name>.sources`. A host that had its repositories in `sources.list` before
  this version loses nothing — the shipped default rewrites the same three
  Debian suites as drop-ins — but the file itself stops being authoritative.
- **Repositories merge, they do not override.** Every variable matching
  `^server_.+_apt_sources$` is merged into one list, so a group adds its
  repositories under its own name (`server_armbian_apt_sources`) and keeps the
  shipped base. Overriding `server_default_apt_sources` replaces the base,
  which is how a non-Debian host swaps the whole layout. Two entries sharing a
  `name` fail the play.
- **An entry overwrites an image-shipped file of the same name.** Naming an
  entry `debian` replaces a vendor `debian.sources`, which is how the duplicate
  base repository on an Armbian or cloud image gets resolved. This only works
  when the vendor file is deb822 (`<name>.sources`): a one-line vendor
  `armbian.list` is untouched by an `armbian` entry -- the role writes
  `armbian.sources` beside it and apt reads both, recreating the duplication
  this change is meant to remove. For a vendor file under some other name, or
  a one-line `.list` file, list it in `server_apt_disable_sources`; it is
  renamed to `<filename>.disabled` and kept. A filename the role writes itself
  is skipped, so listing `debian.sources` there is a no-op rather than a way
  to delete your own base repo.
- **`signed_by` is optional and the Debian default omits it.** apt then
  verifies against `trusted.gpg.d`, as `sources.list` always did. A keyring
  path that does not exist on the host fails `apt update` for every source, so
  only set it where the keyring is known present.
- The root password is hashed with a salt seeded from `inventory_hostname`, so
  it is stable across runs. `server_user.password` is hashed **without** a seed,
  so `user | create` reports `changed` on every run even when nothing differs.

## Check mode

`--check --diff` reports drift in `sshd_config`, `/etc/hosts`, the hostname, the
timezone, the apt sources drop-ins and the package set against a host that has
already been bootstrapped.

Three kinds of probe carry `check_mode: false`, because they only read and later
tasks branch on their output: the `wait_for` port checks in `detect.yml` and
`ssh.yml` -- `wait_for` declares no check mode support, so a skipped result
would leave the `when` beneath it reading an undefined `msg` -- and the two
`needrestart` calls in `packages.yml`, whose `stdout` decides whether the reboot
handler fires. The `reboot` handler itself reports that it would reboot and does
not. Since a check run only simulates the upgrade, `needrestart` reports what
the host needs restarting for right now.

It does not work against a host that has not been bootstrapped yet: `user.yml`
only simulates creating the login user, and every task after it connects as that
user. Run the role for real once first.

Expect one permanent entry in the diff: `user | create` reports `changed` on
every run for the unseeded-hash reason above, in a check run as much as a real
one.

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
