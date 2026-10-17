<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="384">
</div>

# 🔒 OMEGA-JAIL

**Pack de jails pour Fail2ban compatible Omega-serv, Omega-Fire et Omega-Waf**

> Élaboré par **kraynux** pour **Omega-server** 
[kraynux.snake-mackarel](https://kraynux.snake-mackarel.ts.net)

Page officielle : [OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**Langues:**
[Français](README.md) · [English](README.en.md) · [Español](README.es.md) · [Русский](README.ru.md) · [中文](README.zh-CN.md)
---

Catalogue préconfiguré de jails [fail2ban](https://www.fail2ban.org/)
pour `omega-serv` et `omega-waf`.
Au lieu de créer chaque jail à la main dans omega-fire, une seule
commande détecte votre installation omega-serv réelle et installe un
catalogue complet et cohérent, en respectant tout ce qui existe déjà.

Omega-Jail ne remplace rien : omega-fire reste le seul outil qui
surveille/liste/débannit au quotidien ; omega-serv et omega-waf
restent inchangés. Omega-Jail se contente de déposer les fichiers
fail2ban standards (`filter.d/`, `jail.d/`) une fois, de façon
idempotente.

## Pourquoi un ban réseau en plus des bans applicatifs ?

omega-serv (WAF natif, Active Defense) et omega-waf (script magnet)
savent déjà bloquer une requête au niveau HTTP et répondre `451`. Ce
blocage applicatif coûte encore une connexion/un thread. Omega-Jail
porte ces mêmes décisions au niveau réseau (nftables, via fail2ban) :
la connexion est refusée avant même d'atteindre omega-serv, sur tous
les ports — un complément défense-en-profondeur, pas un doublon.

**Exception : Tailscale.** Derrière un tunnel Tailscale, la règle
nftables qui accepte le trafic de confiance passe toujours avant celle
que fail2ban insère pour bannir — le ban réseau devient un no-op pour
ces clients. Chaque jail du catalogue embarque donc un pont : si l'IP
bannie tombe dans la plage Tailscale (`100.64.0.0/10` par défaut), le
ban est relayé vers la blocklist native d'omega-serv, qui répond alors
un `451` explicite — la distinction "banni/pas banni" reste visible
même via Tailscale. Ce pont est toujours *fail-open* : une erreur ici
(omega-serv absent, config introuvable) ne fait jamais échouer le ban
réseau par défaut pour tout le monde.

## Catalogue

| Jail | Source | Déclencheur |
|---|---|---|
| `omega-waf-blocklist-sync` | blocklist du script magnet omega-waf | toute IP déjà bannie par le script |
| `omega-waf-magnet-alerts` | alertes du script magnet omega-waf | 3 alertes / 5 min (même seuil que l'auto-ban du script) |
| `omega-serv-waf-block` | alertes WAF natif omega-serv | 3 blocages réels / 10 min (jamais sur du `log-only`) |
| `omega-serv-active-defense` | journal enrichi Active Defense | 2 requêtes `hostile`/`contained` / 15 min |
| `omega-serv-auth-bruteforce` | log d'accès omega-serv | 5 réponses `401` / 5 min |
| `omega-serv-scan` | log d'accès omega-serv | 15 réponses `404` / 2 min |

Chaque jail n'est installé que si la source correspondante est
réellement configurée côté omega-serv (WAF natif activé, Active
Defense activé, extra `magnet` configuré) — sinon il est signalé comme
non applicable, jamais créé à l'aveugle.

## Installation

```bash
cd omega-jail
./install.sh
```

Crée l'environnement virtuel et installe omega-jail (aucun privilège
root nécessaire pour cette étape).

## Utilisation

Dry-run par défaut — n'écrit jamais rien tant que `--apply` n'est pas
explicitement demandé. `--serv-root` reste obligatoire (aucune
convention ne permet de deviner où vit une installation omega-serv sur
un serveur réel) ; en revanche, les jails doivent toujours aller dans
le VRAI dossier fail2ban de la machine — `/etc/fail2ban/` est donc
détecté et vérifié automatiquement, sans avoir à le préciser :

```bash
./omega-jail.sh --serv-root /chemin/vers/omega-serv
```

Installation réelle (nécessite root — écriture sous `/etc/fail2ban/`,
rechargement de `fail2ban-client`) :

```bash
./omega-jail.sh --serv-root /chemin/vers/omega-serv --apply
```

Si `/etc/fail2ban/` n'existe pas (fail2ban non installé), la commande
échoue proprement avec un message clair plutôt que d'écrire ailleurs
par erreur.

Options utiles :
- `--jail-d-dir`/`--filter-d-dir`/`--action-d-dir <chemin>` : à
  préciser seulement si fail2ban n'est pas installé à l'emplacement
  standard.
- `--only <nom-du-jail>` : n'installer qu'une seule entrée du catalogue.
- `--force` : écraser un `jail.d/omega-jail-<nom>.conf` déjà présent
  (sans cette option, une collision de nom de fichier est toujours
  signalée et jamais écrasée silencieusement).
- `--tailscale-cidr <cidr>` : plage à considérer comme Tailscale, si
  différente de `100.64.0.0/10`.
- `--serv-config <chemin>` : à préciser seulement si la config
  d'omega-serv ne se trouve pas à l'emplacement standard
  (`config/omega-serve.json` sous `--serv-root`).

Chaque exécution est sûre à relancer : un jail déjà créé par un run
précédent (ou par n'importe quel jail externe surveillant déjà le même
fichier de log, quel que soit son nom) est automatiquement détecté et
sauté, jamais dupliqué.

## Prérequis

- `fail2ban` installé (`fail2ban-client` doit être sur le `PATH`).
- Une installation omega-serv existante et configurée (le WAF natif,
  Active Defense et/ou l'extra `magnet` doivent être activés côté
  omega-serv pour que les jails correspondants deviennent applicables).

## Licence

Distribué sous licence MIT. Voir le fichier [LICENSE](LICENSE).
