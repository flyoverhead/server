# `flyoverhead.server.ohmyzsh`

Installs Oh My Zsh with the powerlevel10k theme, a fixed plugin set and the
MesloLGS NF fonts, then makes zsh the user's login shell.

## Role variables

| Variable | Description | Example |
| :--- | :--- | :--- |
| `ohmyzsh_user_name` | User to install for | `{{ ansible_user }}` |
| `ohmyzsh_user_group` | That user's primary group | `{{ ansible_user_gid }}` |
| `ohmyzsh_user_home` | That user's home directory | `{{ ansible_user_dir }}` |
| `ohmyzsh_dependencies` | Packages installed first | Definition example in [defaults/main.yml](defaults/main.yml) |
| `ohmyzsh_install_plugins` | Plugin repositories to clone: `name`, `url`, `branch` | Definition example in [defaults/main.yml](defaults/main.yml) |
| `ohmyzsh_plugins` | Plugins written into the `plugins=(...)` line of `.zshrc` | `[pip, python, ssh-agent]` |
| `ohmyzsh_theme` | `ZSH_THEME` value | `powerlevel10k/powerlevel10k` |
| `ohmyzsh_venv_path` | Virtualenv prepended to `$PATH` in `.zshrc` | `/home/user/.venv` |
| `ohmyzsh_force_reinstall` | Delete `~/.oh-my-zsh` and install again | `false` |

`ohmyzsh_install_plugins` is what gets cloned; `ohmyzsh_plugins` is what gets
enabled. A plugin has to be in both lists to be cloned *and* loaded — the
defaults deliberately clone four and enable one of them
(`zsh-autocomplete`) alongside three plugins that ship with Oh My Zsh.

## Facts set by this role

| Fact | Description |
| :--- | :--- |
| `ohmyzsh_installed` | Whether `~/.oh-my-zsh` already exists; a false value triggers the install block |

## Behaviour worth knowing before the first run

- **The role needs egress to GitHub.** It downloads the Oh My Zsh installer from
  `raw.githubusercontent.com`, clones five repositories from `github.com` and
  pulls four font files from `github.com`. None of it is pinned to a release —
  the plugin clones track a branch and the installer is fetched from `master` —
  so a run reflects upstream at that moment.
- **`~/.zshrc` and `~/.p10k.zsh` are overwritten every run** (`force: True` on
  the template). Local edits to either file are lost.
- The user's login shell is changed to `/bin/zsh`. That takes effect on their
  next login, not in the current session.
- Fonts are installed into `~/.fonts` on the *server*. They only matter if you
  run a desktop session there; for an SSH session it is your **terminal** that
  needs MesloLGS NF installed, otherwise the powerlevel10k prompt renders as
  boxes.
- No tags. The role runs as a whole or not at all.

## Example playbook

```yaml
- hosts: server
  gather_facts: true
  roles:
    - role: flyoverhead.server.ohmyzsh
```
