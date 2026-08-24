# `flyoverhead.server.systemd`

Configures the four systemd subsystems this collection relies on: `firewalld`
(on an nftables backend), `systemd-networkd`, `systemd-resolved` and
`systemd-timesyncd`.

## Role variables

| Variable | Description | Example |
| :--- | :--- | :--- |
| `systemd_default_firewalld` | Firewalld rules | Definition example in [defaults/main.yml](defaults/main.yml) |
| `systemd_networkd` | Networkd interfaces. Empty list disables all networkd management | Definition examples in [defaults/main.yml](defaults/main.yml) |
| `systemd_resolved` | `dns`, `domains`, `cache`, `stub_listener` | Definition example in [defaults/main.yml](defaults/main.yml) |
| `systemd_timesyncd` | `servers`, `fallback_servers` | Definition example in [defaults/main.yml](defaults/main.yml) |

### Merging firewalld rules

[tasks/detect.yml](tasks/detect.yml) collects **every** variable whose name
matches `^systemd.+firewalld$` through the
`community.general.merge_variables` lookup, concatenates them and drops
duplicates. So rather than restating `systemd_default_firewalld`, a caller can
add rules under its own name and both lists apply:

```yaml
# group_vars/web.yml
systemd_web_firewalld:
  - name: https
    port: 443/tcp
    zone: public
    state: enabled
    permanent: true
```

Each rule is passed to `ansible.posix.firewalld`, and any key that module
accepts is supported: `interface`, `masquerade`, `permanent`, `port`,
`port_forward`, `protocol`, `rich_rule`, `service`, `source`, `state`,
`target`, `zone`. `name` is only used as the loop label.

### Networkd interfaces

`kind` picks the template and the file-name priority prefix, which is what
orders interface bring-up:

| `kind` | Priority | Files written |
| :--- | :--- | :--- |
| `ether`, `loopback` | 10 | `.network` |
| `link` | 10 | `.link` |
| `bridge`, `bond` | 20 | `.netdev`, `.network`, `-slaves.network` |
| `vlan` | 30 | `.netdev`, `.network` |
| `ipip` | 40 | `.netdev`, `.network` |

The interface holding the default route is appended automatically if
`systemd_networkd` does not already name it. `ipip` entries naming an `ether`
parent through `device` are attached to that parent as `Tunnel=` entries.

## Facts set by this role

| Fact | Description |
| :--- | :--- |
| `systemd_install` | Whether firewalld, nftables, systemd-resolved or systemd-timesyncd is missing and the install block has to run |
| `systemd_all_firewalld` | The merged, de-duplicated firewalld rule list |
| `systemd_networkd` | Rewritten to include the auto-detected default interface |
| `systemd_networkd_tunnels` | `systemd_networkd` with ipip tunnels attached to their parent interface |
| `systemd_all_networkd` | The above, with a `priority` on every entry |
| `systemd_networkd_managed_devices` | Paths this run wrote, used to delete everything else under `/etc/systemd/network` |

## Tags

`systemd.firewalld`, `systemd.networkd`, `systemd.resolved`,
`systemd.timesyncd`.

## Behaviour worth knowing before the first run

- **A non-empty `systemd_networkd` hands networking to networkd, destructively.**
  The role deletes every `.link`/`.netdev`/`.network` file under
  `/etc/systemd/network` that it did not just write, overwrites
  `/etc/network/interfaces` with a placeholder, masks the legacy `networking`
  service and **queues a reboot handler**. The default is `[]`, which skips all
  of this. Get the interface definition right before you set it on a remote
  host you cannot console into.
- **Switching iptables to the nftables backend also queues a reboot**, via the
  `community.general.alternatives` task in the install block. That block only
  runs when one of the four packages is missing, so in practice it is the first
  run only.
- `resolvconf` is stopped and masked once `resolved.conf` is written, and
  `/etc/systemd/resolved.conf.d/resolved.conf` sets `DNSStubListener` from
  `systemd_resolved.stub_listener`. Leaving the stub listener on means
  `127.0.0.53:53` is occupied — relevant if you later want a resolver of your
  own on port 53.
- On Debian 11 and older the role installs `libnss-resolve` instead of
  `systemd-resolved`, which is a separate package only from Debian 12 on.

## Check mode

`--check --diff` reports drift in the `resolved`, `timesyncd`, `networkd` and
`firewalld` configuration against a host this role has already configured. The
`system | reboot` handler reports that it would reboot and does not.

`firewalld | validate` carries `check_mode: false` because `firewall-cmd
--check-config` only validates and its `rc` is what `failed_when` reads: a
skipped `command` is never put through `changed_when`/`failed_when`, so the
validation -- and the reload it gates -- would silently never happen. In a check
run the firewalld rules that notified it were not applied, so it validates the
configuration the host currently has on disk.

## Example playbook

```yaml
- hosts: server
  gather_facts: true
  vars:
    systemd_networkd:
      - name: lo
        kind: loopback
        addresses:
          - 127.0.0.1/8
      - name: eth0
        kind: ether
        address: dhcp
  roles:
    - role: flyoverhead.server.server
    - role: flyoverhead.server.systemd
```

Run `flyoverhead.server.server` first: `systemd_default_firewalld` opens
`ansible_port`, which is the port that role moves sshd onto.
