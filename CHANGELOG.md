# Changelog

All notable changes to `flyoverhead.server`.

## 2.1.0

### Changed

- **Python packages are installed with uv instead of pip.** `tasks/packages.yml`
  now creates `server_pip_pyenv_path` with `uv venv` and populates it with
  `uv pip install`; `ansible.builtin.pip` is gone. Variable names are unchanged,
  so no consumer needs editing.
- `server_packages` drops `python3-pip`. `python3-venv` stays, unused but
  harmless, so that already-provisioned hosts see no removal.
- `server_pip_packages` now defaults to `[]` rather than `[pip]`, and the
  install task is skipped when it is empty. The virtualenv is still created
  unconditionally, because `ohmyzsh`'s `zshrc.j2` puts its `bin` on `PATH`.
- **`--check` no longer reports what these tasks would do.** The venv and
  package-install tasks are `ansible.builtin.command`, which has no check-mode
  support, so both now show as *skipped* rather than *changed* under
  `--check --diff`; `ansible.builtin.pip` reported real check-mode diffs. The
  `uv | install` task's `ansible.builtin.unarchive` skips itself in check mode
  too, for the same reason.

### Added

- `tasks/uv.yml` installs a pinned uv release tarball into `/usr/local/bin`,
  selected for `ansible_architecture`, under the new `server.uv` tag. Bumping
  `server_uv_version` reinstalls, because the guard tests `uv --version`
  rather than the file's existence.

### Removed

- The venv no longer contains `pip`. `uv venv` does not seed one; add
  `--seed` to the `create virtualenv` task if something outside this
  collection calls `<venv>/bin/pip`.
## 2.0.3

### Fixed

- **Port detection no longer downgrades a working host to port 22.** 2.0.2
  probed port 22 from the controller and read "the connect did not time out"
  as "this host still uses the default port". A host whose port 22 accepts a
  TCP connection and immediately closes it — a tarpit, or a provider-level
  drop — therefore had `ansible_port` set to 22, and every later task failed
  `UNREACHABLE`. With `ignore_unreachable: true` in the calling playbook the
  whole run then reported `rc=0`, `changed=0` and looked like a clean no-op.
  The custom port is now probed first and kept when it answers; 22 is probed
  only as a fallback.
- **Both port probes now require an SSH banner** (`search_regex: SSH-`)
  rather than accepting any TCP connect, in `detect.yml` and in `ssh.yml`'s
  migration guard. A port that accepts and closes is no longer mistaken for
  a listening sshd.

## 2.0.2

### Fixed

- **Bootstrapping a fresh host works again.** 2.0.0 moved the apt source merge
  into `tasks/detect.yml`, but `server_default_apt_sources` interpolates
  `ansible_distribution_release`, and no fact can exist before credentials are
  established — which happens in `tasks/user.yml`, included *after* `detect`.
  Every fresh host in every group therefore died on
  `'ansible_distribution_release' is undefined`. The merge and its three
  assertions now run in `user.yml`, after facts are guaranteed and still ahead
  of the first use of `server_apt_sources`.

- **The `wait_for` port probes now run from the controller.** Those in
  `detect.yml` and `ssh.yml` had no `delegate_to`, so Ansible connected *to the
  target* to test whether the target was reachable. `detect.yml` consequently
  set `ansible_port: 22` whenever a host was unreachable on its custom port,
  whether or not 22 was open. Both are delegated to `localhost` with
  `become: false`.

- **The `msg` guards beneath those probes tolerate success.** `wait_for` sets no
  `msg` when the port is already open, so the bare `server_*_ssh_port.msg`
  references raised once delegation made that path reachable. Both now use
  `| default("")`.

- **`detect.yml` no longer depends on the playbook setting
  `ignore_unreachable`.** `detect | gather remote facts` and
  `detect | connection to host` are expected to fail before bootstrap and carry
  the directive themselves.

## 2.0.1

### Fixed

- **`zsh-autocomplete` completions are registered again.** Its functions live in
  a `Completions/` directory that only joins `$fpath` when the plugin is
  sourced, which Oh My Zsh does *after* running `compinit` — so they were never
  registered and every completion raised
  `command not found: _autocomplete__unambiguous`. The directory now goes on
  `$fpath` before the first `compinit`. Rendered only for hosts whose
  `ohmyzsh_plugins` contains `zsh-autocomplete`.

## 2.0.0

### Changed

- **server**: apt configuration is now one merged, distro-agnostic list, and
  `/etc/apt/sources.list` is emptied to a comment in favour of `sources.list.d`
  drop-ins.

  `sources.list.j2` could express exactly one shape — three Debian suites off
  one `server_apt_mirror`, with `-security` concatenated onto that URL for the
  security suite. Ubuntu serves security from the same URI and Armbian has no
  security suite at all plus its own component names, so neither fitted.
  (Ubuntu here is an untested capability of the new interface, not a
  supported platform -- `meta/main.yml` still declares Debian only.)

  Repositories are now described by any variable matching
  `^server_.+_apt_sources$`, merged into one list with
  `community.general.merge_variables` — the idiom the `systemd` role already
  uses for firewalld. Merging rather than overriding is deliberate: Ansible
  cannot merge lists across group_vars, so a single variable would mean a group
  adding one repository silently dropping the base. One entry is one file is
  one deb822 stanza; every field but `name` takes a scalar or a list. Two
  entries sharing a `name` fail the play; last-wins was rejected too, since
  `merge_variables` documents no ordering guarantee (it happens to sort
  variable names alphabetically, which is not a semantic worth relying on).

  `server_apt_mirror` and `server_apt_components` survive, now feeding only the
  shipped `server_default_apt_sources`, so a fleet whose hosts differ by mirror
  hostname keeps its one-line overrides.

  New `server_apt_disable_sources` renames image-shipped source files out of
  the way, filtered against the names this role writes.

  Both shipped entries also carry `signed_by`, pinned to
  `/usr/share/keyrings/debian-archive-keyring.gpg`, scoping each to the Debian
  archive key rather than trusting everything in `trusted.gpg.d`. An earlier
  draft omitted it, on the theory that an absent `Signed-By` path fails `apt
  update` for every source on the host; measured on a live Debian 13 host,
  a broken path fails only that one entry, and `apt-get update` still exits 0
  regardless -- the failure is silent either way, which is the actual argument
  for pinning a keyring you know is present rather than the one against
  omitting it.

### Migration

- Callers setting `server_apt_mirror` or `server_apt_components` need no change.
- Callers relying on `/etc/apt/sources.list` being authoritative do: it is now
  a comment. The same repositories are written as drop-ins.
- An image that ships its own base repository in `sources.list.d` was
  previously duplicated against `sources.list`. If it is named
  `debian.sources`, the default entry now overwrites it. If it is named
  anything else, list it in `server_apt_disable_sources`.

## 1.0.2

### Changed

- Collection README only. Status badges for the collection version,
  ansible-core requirement, license, supported platform and role count, and
  section headings in an order shared with `flyoverhead.docker` and
  `flyoverhead.hosting` so the three read as one set. The three destructive
  behaviours -- the `sshd_config` and `sources.list` replacements and the
  networkd takeover -- moved under a Gotchas heading and deliberately stayed
  expanded. The license badge reads `GPL-3.0-only`; the `fail2ban` Apache-2.0
  exception remains in the License prose, which a badge cannot carry. No role,
  task, template or default changed; releasing it only so the README that ships
  in the Galaxy tarball matches the repository.

## 1.0.1

### Fixed

- **Check mode**: `ansible-playbook --check --diff` now completes against a host
  this collection has already bootstrapped. The roles performed state discovery
  with modules ansible-core does not execute in a check run and then
  dereferenced the registered result unconditionally. Nothing in the collection
  had ever set `check_mode`.
- **server**: `detect | default ssh port` and `ssh | check custom port` are
  `ansible.builtin.wait_for`, which declares no check mode support and is
  therefore skipped in a check run. Both are followed by a task that branches on
  the registered `msg`, so the play aborted on an undefined attribute. Both
  probes now carry `check_mode: false` -- they only read a port.
- **server**: the two `needrestart` calls in `packages.yml` are
  `ansible.builtin.command`, which skips itself in a check run unless given
  `creates`/`removes`, so `changed_when` had no `stdout` and the reboot handler
  was unreachable: a check run said nothing about a host needing a restart. Both
  now carry `check_mode: false`. The `reboot` handler itself already reports
  without rebooting.
- **systemd**: `firewalld | validate` is an `ansible.builtin.command` and was
  skipped in a check run. A skipped result is never put through
  `changed_when`/`failed_when`, so the validation -- and the `firewalld | reload`
  it gates -- silently never happened. It now carries `check_mode: false`.

### Changed

- Every role README gained a `## Check mode` section stating what a check run
  covers and what it cannot -- notably that `server` cannot be checked against a
  host that has not been bootstrapped, because `user.yml` only simulates
  creating the login user every later task connects as.

## 1.0.0

Initial release. The four remote-configuration roles were extracted from the
`new_lab` repository, where they lived as loose local roles under `roles/`, and
each one gained a README and a `meta/main.yml`.

### Fixed

These are all cases where a role's own default was unusable, and only worked in
`new_lab` because an inventory variable happened to override it. Anyone
installing the collection and running it unmodified would have hit them.

- **server**: `server_user.authorized_ssh_keys` defaulted to `id_ed25519.pub`,
  but `tasks/user.yml` appends `.pub` itself, so the lookup went looking for
  `id_ed25519.pub.pub` and failed. The default is now `id_ed25519`.
- **systemd**: `systemd_default_firewalld` set `port: '{{ ansible_port }}'`,
  which `ansible.posix.firewalld` rejects — it requires `PORT/PROTOCOL`. Now
  `'{{ ansible_port }}/tcp'`.
- **systemd**: the networkd default was named `systemd_default_networkd` while
  `tasks/detect.yml` reads `systemd_networkd`, so the role failed on an
  undefined variable unless the caller defined it. Renamed to `systemd_networkd`.
- **fail2ban**: `jail.local` referenced the `telegram` action unconditionally,
  but `telegram.conf` is only written when a bot token is configured. With the
  default empty token fail2ban refused to start on an unknown action. The action
  is now only listed when both the token and the chat ID are set.

### Changed

- **fail2ban**: the `[DEFAULT]` jail settings moved out of the template into
  variables — `fail2ban_bantime`, `fail2ban_findtime`, `fail2ban_maxretry`,
  `fail2ban_backend`, `fail2ban_destemail`, `fail2ban_sendername`,
  `fail2ban_mta` and `fail2ban_sshd_mode`. Values are unchanged except
  `destemail`, which was a hardcoded personal address and now defaults to
  `root@localhost`.
- **systemd**: the commented networkd examples in `defaults/main.yml` were
  rewritten onto RFC 5737 documentation addresses and `example.com`. They
  previously carried real internal topology.
- **all roles**: internal registers and set_facts gained their role prefix, so
  the collection passes `ansible-lint` at the `production` profile like
  `flyoverhead.docker` does. The only externally visible one is
  `ssh_port` -> `server_ssh_port`, which a caller can set to pin the target sshd
  port. `ssh_host`, `check_connection_result`, `ssh_socket_config`,
  `default_ssh_port`, `custom_ssh_port`, `ssh_socket_unit_file`,
  `root_password`, `kernel_upgrade` and `libraries_upgrade` gained a `server_`
  prefix; the `networkd_*` registers and `firewalld_config_valid` gained a
  `systemd_` one; `repo_clone` and the `ohmyzsh` stat register gained an
  `ohmyzsh_` one.

### Known issues

- **server**: `server_user.password` is hashed without a salt seed, so
  `user | create` reports `changed` on every run even when nothing differs. The
  root password task seeds its salt from `inventory_hostname` and is idempotent.
- The test harness does not cover `server/tasks/ssh.yml`, the sshd port
  migration. See the collection README.
