# Changelog

All notable changes to `flyoverhead.server`.

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
