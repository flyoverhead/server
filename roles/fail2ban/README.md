# `flyoverhead.server.fail2ban`

Installs fail2ban and configures an `[sshd]` jail that bans through firewalld
rich rules, with optional Telegram notifications on ban and unban.

## Role variables

| Variable | Description | Example |
| :--- | :--- | :--- |
| `fail2ban_bantime` | Ban duration, seconds | `3600` |
| `fail2ban_findtime` | Window in which `maxretry` failures trigger a ban, seconds | `600` |
| `fail2ban_maxretry` | Failures before a ban | `3` |
| `fail2ban_backend` | fail2ban log backend | `auto` |
| `fail2ban_destemail` | Address mail actions send to | `root@localhost` |
| `fail2ban_sendername` | Sender name on those mails | `Fail2Ban` |
| `fail2ban_mta` | Mail transport fail2ban invokes | `sendmail` |
| `fail2ban_sshd_mode` | `mode` of the `[sshd]` jail filter | `ddos` |
| `fail2ban_telegram_bot_token` | Telegram bot token. Empty disables notifications | `''` |
| `fail2ban_telegram_chat_id` | Telegram chat to notify. Empty disables notifications | `''` |

Telegram is configured only when **both** the token and the chat ID are
non-empty. The token is rendered into `/etc/fail2ban/scripts/telegram.sh` on the
managed host in cleartext (mode `0750`, root-owned), so supply it from a vault.

## Facts set by this role

| Fact | Description |
| :--- | :--- |
| `fail2ban_installed` | Whether the `fail2ban` package is already present; a false value triggers the install task |

## Dependencies

| Name | Description |
| :--- | :--- |
| `flyoverhead.server.systemd` | [README.md](../systemd/README.md) — supplies firewalld, which `banaction` needs |
| `flyoverhead.server.server` | [README.md](../server/README.md) — moves sshd onto `ansible_port`, which the jail watches |

`banaction` is `firewallcmd-rich-rules`, so fail2ban cannot start without a
running firewalld. The `[sshd]` jail's `port` is `ansible_port`, so the `server`
role has to have moved sshd there first or the jail watches the wrong port.

## Behaviour worth knowing before the first run

- `/var/log/auth.log` is created if missing. On a host using journald-only
  logging the file stays empty and the jail never fires — `backend = auto`
  resolves to the file backend because `logpath` is set. Set
  `fail2ban_backend: systemd` for journald-only hosts.
- `mode = ddos` matches connection-teardown patterns rather than failed
  password attempts. That catches port scanners on a key-only host, where
  `mode = normal` would see nothing.
- The mail actions are configured but nothing installs an MTA. Without
  `sendmail` on the host the mail action fails silently; Telegram is the path
  that actually reports.
- No tags. The role runs as a whole or not at all.

## Attribution

This role began as a fork of
[`robertdebock.fail2ban`](https://github.com/robertdebock/ansible-role-fail2ban)
and keeps its original **Apache-2.0** licence, which is why
[meta/main.yml](meta/main.yml) differs from the GPL-3.0-only of the rest of the
collection.

## Check mode

`--check --diff` reports drift in `fail2ban.local`, `jail.local` and the telegram
action against a host where fail2ban is already installed, and the restart
handler reports what it would do. Nothing in the role needs special handling in
a check run.

Against a host without the package the apt install is simulated and the
configuration is reported as pending, which is accurate -- but fail2ban is not
there to validate it.

## Example playbook

```yaml
- hosts: server
  gather_facts: true
  vars:
    ansible_port: 33731
    fail2ban_telegram_bot_token: '{{ vault_telegram_bot_token }}'
    fail2ban_telegram_chat_id: '{{ vault_telegram_chat_id }}'
  roles:
    - role: flyoverhead.server.server
    - role: flyoverhead.server.systemd
    - role: flyoverhead.server.fail2ban
```
