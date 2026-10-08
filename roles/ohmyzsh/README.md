# `flyoverhead.server.ohmyzsh`

Installs Oh My Zsh, the starship prompt and a fixed plugin set, writes
`.zshrc` and `~/.config/starship.toml`, then makes zsh the user's login shell.

## Role variables

| Variable | Description | Example |
| :--- | :--- | :--- |
| `ohmyzsh_user_name` | User to install for | `{{ ansible_user }}` |
| `ohmyzsh_user_group` | That user's primary group | `{{ ansible_facts.user_gid }}` |
| `ohmyzsh_user_home` | That user's home directory | `{{ ansible_facts.user_dir }}` |
| `ohmyzsh_dependencies` | Packages installed on every run; `starship` is one of them | Definition example in [defaults/main.yml](defaults/main.yml) |
| `ohmyzsh_install_plugins` | Plugin repositories to clone: `name`, `url`, `branch` | Definition example in [defaults/main.yml](defaults/main.yml) |
| `ohmyzsh_plugins` | Plugins written into the `plugins=(...)` line of `.zshrc` | `[pip, python, ssh-agent]` |
| `ohmyzsh_starship_settings` | The whole starship config as a mapping, rendered to TOML | Definition example in [defaults/main.yml](defaults/main.yml) |
| `ohmyzsh_starship_settings_extra` | Merged recursively over `ohmyzsh_starship_settings` | `{time: {disabled: true}}` |
| `ohmyzsh_starship_config_path` | Where the config is written | `/home/user/.config/starship.toml` |
| `ohmyzsh_venv_path` | Virtualenv prepended to `$PATH` in `.zshrc` | `/home/user/.venv` |
| `ohmyzsh_force_reinstall` | Delete `~/.oh-my-zsh` and install again | `false` |

`ohmyzsh_install_plugins` is what gets cloned; `ohmyzsh_plugins` is what gets
enabled. A plugin has to be in both lists to be cloned *and* loaded — the
defaults deliberately clone four and enable one of them
(`zsh-autocomplete`) alongside three plugins that ship with Oh My Zsh.

## Facts set by this role

| Fact | Description |
| :--- | :--- |
| `ohmyzsh_installed` | Whether `~/.oh-my-zsh` already exists; a false value runs the installer |

## Behaviour worth knowing before the first run

- **The role needs egress to GitHub.** It downloads the Oh My Zsh installer from
  `raw.githubusercontent.com` and clones four plugin repositories from
  `github.com`. None of it is pinned to a release —
  the plugin clones track a branch and the installer is fetched from `master` —
  so a run reflects upstream at that moment.
- **`~/.zshrc` and `starship.toml` are overwritten every run**, each with a
  backup beside it. Local additions belong in `~/.zshrc.d/*.zsh`, sourced last,
  or `~/.aliases`; prompt changes belong in `ohmyzsh_starship_settings_extra`.
  `.zshrc` is checked with `zsh -n` before it replaces the old one.
- **starship comes from the distribution's apt repository**: 1.22.1 on Debian
  13. The default config is the same as `flyoverhead.macos.ohmyzsh`'s and
  works on 1.22.1. A key added for a newer starship only produces a warning
  when the prompt renders. An inventory that sets its own
  `ohmyzsh_dependencies` has to keep `starship` in it.
- **Upgrading from 3.x removes `~/.p10k.zsh` and the cloned powerlevel10k
  theme.** Fonts installed into `~/.fonts` by earlier versions are left alone.
- The user's login shell is changed to `/bin/zsh`. That takes effect on their
  next login, not in the current session.
- **The prompt's icons come from your terminal's font.** Over SSH it is the
  client that needs a Nerd Font such as MesloLGS NF; without one the prompt
  renders boxes.
- No tags. The role runs as a whole or not at all.

## Check mode

`--check --diff` reports drift in `.zshrc` and `starship.toml` against a host where
oh-my-zsh is already installed.

`install | oh-my-zsh` is a `command` with `creates`, which is the one form of
`command` that reports something useful in a check run: once the install exists
it reports that it would not run. Against a host without oh-my-zsh the installer
and the plugin clones are reported as pending without running, so the `.zshrc`
diff is rendered against a prompt and plugin set that are not on the host yet.

## Example playbook

```yaml
- hosts: server
  gather_facts: true
  roles:
    - role: flyoverhead.server.ohmyzsh
```
