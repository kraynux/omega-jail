<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="384">
</div>

# 🔒 OMEGA-JAIL

**Fail2ban jail pack compatible with Omega-serv, Omega-Fire and Omega-Waf**

> Developed by [kraynux](https://github.com/kraynux) for [Omega-Server](https://kraynux.snake-mackarel.ts.net)   

Official page: [OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**Languages:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

Preconfigured catalog of [fail2ban](https://www.fail2ban.org/) jails
for `omega-serv` and `omega-waf`.
Instead of creating each jail by hand in omega-fire, a single command
detects your real omega-serv installation and installs a complete,
consistent catalog, respecting everything that already exists.

Omega-Jail replaces nothing: omega-fire remains the only tool that
monitors/lists/unbans on a day-to-day basis; omega-serv and omega-waf
stay unchanged. Omega-Jail only drops the standard fail2ban files
(`filter.d/`, `jail.d/`) once, idempotently.

## Why a network-level ban in addition to application-level bans?

omega-serv (native WAF, Active Defense) and omega-waf (magnet script)
already know how to block a request at the HTTP level and answer
`451`. That application-level block still costs a connection/a
thread. Omega-Jail carries the same decisions over to the network
level (nftables, via fail2ban): the connection is refused before it
even reaches omega-serv, on every port — a defense-in-depth
complement, never a duplicate.

**Exception: Tailscale.** Behind a Tailscale tunnel, the nftables rule
that accepts trusted traffic always runs before the one fail2ban
inserts to ban — the network ban becomes a no-op for those clients.
Every jail in the catalog therefore carries a bridge: if the banned IP
falls within the Tailscale range (`100.64.0.0/10` by default), the ban
is relayed to omega-serv's native blocklist, which then answers an
explicit `451` — the "banned/not banned" distinction stays visible
even over Tailscale. This bridge is always *fail-open*: an error here
(omega-serv missing, config not found) never makes the default network
ban fail for everyone else.

**Behind a local proxy (Tailscale Funnel, reverse proxy on the same machine).** Connections then come from the local host: the network ban never reaches the visitor. Omega-Jail detects it (omega-serv trusted proxy covering `127.0.0.1` or `::1`) and the bridge then relays every ban of a public address to the omega-serv blocklist, which answers `451` — the same path as the magnet script. RIPOSTE jails are not relayed: RIPOSTE has already set its local ban.

**Networks never banned.** Only external traffic can be banned: localhost, Tailscale (`100.64.0.0/10`) and the local network never are. Each generated jail gets an `ignoreip` line with the list **provided by omega-serv itself** (`omega-serv waf never-auto-block`, setting `options.waf.reputation.never_auto_block`) — never a hard-coded copy here. An `ignoreip` already defined in `[DEFAULT]` is kept and extended, never overwritten. The Tailscale bridge never relays the ban of an exempt address: with the default settings it therefore relays nothing anymore (your external visitors arrive with their real public address). Except behind a local proxy: see the previous paragraph. If omega-serv is missing or too old, only localhost is exempt, with a warning in the report. An existing installation is only updated with `--apply --force`.

## Catalog

**10 jails**: 6 base jails, installed once, and 4 RIPOSTE jails, installed for **each** omega-serv instance (prefixed with its service name, e.g. `omega-serv-riposte-1h`).

| Jail | Source | Trigger |
|---|---|---|
| `omega-waf-blocklist-sync` | omega-waf magnet script blocklist | any IP already banned by the script |
| `omega-waf-magnet-alerts` | omega-waf magnet script alerts | 3 alerts / 5 min (same threshold as the script's own auto-ban) |
| `omega-serv-waf-block` | omega-serv native WAF alerts | 3 real blocks / 10 min (never on `log-only`) |
| `omega-serv-active-defense` | Active Defense enriched log | 2 `hostile`/`contained` requests / 15 min |
| `omega-serv-auth-bruteforce` | omega-serv access log | 5 `401` responses / 5 min |
| `omega-serv-scan` | omega-serv access log | 15 `404` responses / 2 min |
| `<service>-riposte-1h` | RIPOSTE network bans (omega-serv 2.1.0), one set per instance | tiers from 1 h to under 6 h: 1 h ban |
| `<service>-riposte-6h` | RIPOSTE network bans (omega-serv 2.1.0), one set per instance | tiers from 6 h to under 24 h: 6 h ban |
| `<service>-riposte-24h` | RIPOSTE network bans (omega-serv 2.1.0), one set per instance | tiers from 24 h to under 7 days: 24 h ban |
| `<service>-riposte-7d` | RIPOSTE network bans (omega-serv 2.1.0), one set per instance | tiers of 7 days or more: 7-day ban |

Each jail is only installed if its corresponding source is actually
configured on the omega-serv side (native WAF enabled, Active Defense
enabled, `magnet` extra configured, RIPOSTE enabled with network bans) —
otherwise it is reported as not applicable, never created blindly.

**RIPOSTE jails (since 1.1.0).** RIPOSTE, the graduated response module
of omega-serv 2.1.0, writes each of its network bans to its journal;
Omega-Jail installs four fixed-duration jails (1 h, 6 h, 24 h, 7 days)
and each RIPOSTE tier goes to the longest one that does not exceed it.
Every omega-serv instance on the machine is detected automatically
(systemd services and the instance registry): each one gets its own
jails, prefixed with its service name.

## Installation

```bash
[ -d omega-jail ] && echo "ℹ️ Already extracted here, skipping." || tar -xzf omega-jail.tar.gz
cd omega-jail/
chmod +x install.sh
./install.sh
```

`install.sh` creates the virtual environment, installs omega-jail
(`pip install -e .`, no root privileges needed for this step), makes
`omega-jail.sh`/`install.sh` executable — then asks for the path of
the omega-serv installation to protect: if you already know it, typing
it directly is fastest (skips the search entirely); left blank, an
automatic search under `$HOME` takes over (recognized by the presence
of `omega-serv.sh`, a few seconds) — a single candidate is saved
automatically; zero or several, it asks you again. That path is
remembered in `.serv-root` (never committed): you never have to type
it again afterward.

**Updating.** From the parent folder, extract the archive over the existing folder (`tar -xzf omega-jail.tar.gz`, without the “Already extracted” guard above), then run `./install.sh` again: the omega-serv path already saved is kept. If the catalog contains new applicable jails (for example the RIPOSTE jails of 1.1.0), they are listed and then installed after confirmation (`sudo`); jails already installed are never touched. Omega-Fire then shows them automatically, with no further setting.

## Usage

Dry-run by default — never writes anything until `--apply` is
explicitly requested. No path to type: omega-serv is the one saved by
`install.sh`, and the jails must always go into the REAL fail2ban
directory on the machine — `/etc/fail2ban/` is therefore also
detected and verified automatically:

```bash
./omega-jail.sh
```

Real installation (requires root — writes under `/etc/fail2ban/`,
reloads `fail2ban-client`):

```bash
./omega-jail.sh --apply
```

If `/etc/fail2ban/` doesn't exist (fail2ban not installed), the
command fails cleanly with a clear message instead of writing
somewhere wrong by mistake.

Useful options:
- `--serv-root`: takes the path of a different omega-serv to target
  just this once, instead of the one saved by `install.sh`.
- `--jail-d-dir`, `--filter-d-dir`, `--action-d-dir`: each take a
  directory path, only needed if fail2ban isn't installed at the
  standard location.
- `--only`: takes the name of a catalog jail, to install a single
  entry only (`--only riposte-7d`: the 7-day RIPOSTE jail of every
  instance).
- `--force`: overwrites an existing `jail.d/` file for a catalog jail
  (without this option, a filename collision is always reported and
  never silently overwritten).
- `--tailscale-cidr`: takes a CIDR network range to treat as
  Tailscale, if different from `100.64.0.0/10`.
- `--serv-config`: takes a path, only needed if omega-serv's config
  isn't at the standard location (`config/omega-serve.json` under the
  omega-serv path in use).

Every run is safe to repeat: a jail already created by a previous run
(or any external jail already watching the same log file, under any
name) is automatically detected and skipped, never duplicated.

## Requirements

- `fail2ban` installed (`fail2ban-client` must be on `PATH`).
- An existing, configured omega-serv installation (native WAF, Active
  Defense and/or the `magnet` extra must be enabled on the omega-serv
  side for the corresponding jails to become applicable).

## License

Distributed under the MIT license. See the [LICENSE](../../../LICENSE) file.
