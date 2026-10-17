<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="384">
</div>

# 🔒 OMEGA-JAIL

**Fail2ban jail pack compatible with Omega-serv, Omega-Fire and Omega-Waf**

> Developed by **kraynux** for **Omega-server** 
[kraynux.snake-mackarel](https://kraynux.snake-mackarel.ts.net)

Official page: [OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**Languages:**
[Français](README.md) · [English](README.en.md) · [Español](README.es.md) · [Русский](README.ru.md) · [中文](README.zh-CN.md)
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

## Catalog

| Jail | Source | Trigger |
|---|---|---|
| `omega-waf-blocklist-sync` | omega-waf magnet script blocklist | any IP already banned by the script |
| `omega-waf-magnet-alerts` | omega-waf magnet script alerts | 3 alerts / 5 min (same threshold as the script's own auto-ban) |
| `omega-serv-waf-block` | omega-serv native WAF alerts | 3 real blocks / 10 min (never on `log-only`) |
| `omega-serv-active-defense` | Active Defense enriched log | 2 `hostile`/`contained` requests / 15 min |
| `omega-serv-auth-bruteforce` | omega-serv access log | 5 `401` responses / 5 min |
| `omega-serv-scan` | omega-serv access log | 15 `404` responses / 2 min |

Each jail is only installed if its corresponding source is actually
configured on the omega-serv side (native WAF enabled, Active Defense
enabled, `magnet` extra configured) — otherwise it is reported as not
applicable, never created blindly.

## Installation

```bash
cd omega-jail
./install.sh
```

Creates the virtual environment and installs omega-jail (no root
privileges needed for this step).

## Usage

Dry-run by default — never writes anything until `--apply` is
explicitly requested. `--serv-root` remains mandatory (there is no
convention that lets us guess where an omega-serv installation lives
on a real server); the jails, however, must always go into the REAL
fail2ban directory on the machine — `/etc/fail2ban/` is therefore
detected and verified automatically, with nothing to specify:

```bash
./omega-jail.sh --serv-root /path/to/omega-serv
```

Real installation (requires root — writes under `/etc/fail2ban/`,
reloads `fail2ban-client`):

```bash
./omega-jail.sh --serv-root /path/to/omega-serv --apply
```

If `/etc/fail2ban/` doesn't exist (fail2ban not installed), the
command fails cleanly with a clear message instead of writing
somewhere wrong by mistake.

Useful options:
- `--jail-d-dir`/`--filter-d-dir`/`--action-d-dir <path>`: only needed
  if fail2ban isn't installed at the standard location.
- `--only <jail-name>`: install a single catalog entry only.
- `--force`: overwrite an existing `jail.d/omega-jail-<name>.conf`
  (without this option, a filename collision is always reported and
  never silently overwritten).
- `--tailscale-cidr <cidr>`: range to treat as Tailscale, if different
  from `100.64.0.0/10`.
- `--serv-config <path>`: only needed if omega-serv's config isn't at
  the standard location (`config/omega-serve.json` under
  `--serv-root`).

Every run is safe to repeat: a jail already created by a previous run
(or any external jail already watching the same log file, under any
name) is automatically detected and skipped, never duplicated.

## Requirements

- `fail2ban` installed (`fail2ban-client` must be on `PATH`).
- An existing, configured omega-serv installation (native WAF, Active
  Defense and/or the `magnet` extra must be enabled on the omega-serv
  side for the corresponding jails to become applicable).

## License

Distributed under the MIT license. See the [LICENSE](LICENSE) file.
