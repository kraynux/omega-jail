<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="384">
</div>

# 🔒 OMEGA-JAIL

**Pack de jails pour Fail2ban compatible Omega-serv, Omega-Fire et Omega-Waf**

> Élaboré par [kraynux](https://github.com/kraynux) pour [Omega-Server](https://kraynux.snake-mackarel.ts.net)   

Page officielle : [OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**Langues :**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](docs/translation/en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](docs/translation/es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](docs/translation/pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](docs/translation/it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](docs/translation/de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](docs/translation/nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](docs/translation/pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](docs/translation/ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](docs/translation/zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](docs/translation/vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](docs/translation/th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](docs/translation/id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](docs/translation/ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](docs/translation/ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](docs/translation/hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](docs/translation/ar/README.md)

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

**Derrière un proxy local (Tailscale Funnel, reverse proxy sur la même machine).** Les connexions arrivent alors de l'hôte local : le ban réseau ne touche jamais le visiteur. Omega-Jail le détecte (proxy de confiance d'omega-serv couvrant `127.0.0.1` ou `::1`) et le pont relaie alors tout ban d'une adresse publique vers la blocklist d'omega-serv, qui répond `451` — le même circuit que le script magnet. Les jails RIPOSTE ne sont pas relayés : RIPOSTE a déjà posé son ban local.

**Réseaux jamais bannis.** Seul le trafic externe peut être banni : l'hôte local, Tailscale (`100.64.0.0/10`) et le réseau local ne le sont jamais. Chaque jail généré reçoit une ligne `ignoreip` avec la liste **fournie par omega-serv lui-même** (`omega-serv waf never-auto-block`, réglage `options.waf.reputation.never_auto_block`) — jamais une copie en dur ici. Un `ignoreip` déjà défini dans `[DEFAULT]` est conservé et complété, jamais écrasé. Le pont Tailscale ne relaie jamais le ban d'une adresse exemptée : avec les réglages par défaut, il ne relaie donc plus rien (vos visiteurs externes arrivent avec leur vraie adresse publique). Sauf derrière un proxy local : voir le paragraphe précédent. omega-serv introuvable ou trop ancien : seul l'hôte local est exempté, avec un avertissement dans le rapport. Une installation existante reçoit ces réseaux à la mise à jour suivante (jail listé « à mettre à jour »).

## Catalogue

**10 jails** : 6 jails de base, installés une seule fois, et 4 jails RIPOSTE, installés pour **chaque** instance omega-serv (préfixés par le nom de son service, ex. `omega-serv-riposte-1h`).

| Jail | Source | Déclencheur |
|---|---|---|
| `omega-waf-blocklist-sync` | blocklist du script magnet omega-waf | toute IP déjà bannie par le script |
| `omega-waf-magnet-alerts` | alertes du script magnet omega-waf | 3 alertes / 5 min (même seuil que l'auto-ban du script) |
| `omega-serv-waf-block` | alertes WAF natif omega-serv | 3 blocages réels / 10 min (jamais sur du `log-only`) |
| `omega-serv-active-defense` | journal enrichi Active Defense | 2 requêtes `hostile`/`contained` / 15 min |
| `omega-serv-auth-bruteforce` | log d'accès omega-serv | 5 réponses `401` / 5 min |
| `omega-serv-scan` | log d'accès omega-serv | 15 réponses `404` / 2 min |
| `<service>-riposte-1h` | bans réseau de RIPOSTE (omega-serv 2.1.0), un jeu par instance | paliers de 1 h à moins de 6 h : ban de 1 h |
| `<service>-riposte-6h` | bans réseau de RIPOSTE (omega-serv 2.1.0), un jeu par instance | paliers de 6 h à moins de 24 h : ban de 6 h |
| `<service>-riposte-24h` | bans réseau de RIPOSTE (omega-serv 2.1.0), un jeu par instance | paliers de 24 h à moins de 7 jours : ban de 24 h |
| `<service>-riposte-7d` | bans réseau de RIPOSTE (omega-serv 2.1.0), un jeu par instance | paliers de 7 jours et plus : ban de 7 jours |

Chaque jail n'est installé que si la source correspondante est
réellement configurée côté omega-serv (WAF natif activé, Active
Defense activé, extra `magnet` configuré, RIPOSTE activé avec le ban
réseau) — sinon il est signalé comme non applicable, jamais créé à
l'aveugle.

**Jails RIPOSTE (depuis la 1.1.0).** RIPOSTE, le module de riposte
graduée d'omega-serv 2.1.0, écrit chacun de ses bans réseau dans son
journal ; Omega-Jail installe quatre jails de durée fixe (1 h, 6 h,
24 h, 7 jours) et chaque palier RIPOSTE va à la plus longue qui ne le
dépasse pas. Toutes les instances omega-serv de la machine sont
détectées automatiquement (services systemd et registre des instances) :
chacune reçoit ses propres jails, préfixées par le nom de son service.

## Installation

```bash
[ -d omega-jail ] && echo "ℹ️ Déjà extrait ici, étape ignorée." || tar -xzf omega-jail.tar.gz
cd omega-jail/
chmod +x install.sh
./install.sh
```

`install.sh` crée l'environnement virtuel, installe omega-jail
(`pip install -e .`, aucun privilège root nécessaire pour cette étape),
rend `omega-jail.sh`/`install.sh` exécutables — puis demande le chemin
de l'installation omega-serv à protéger : si vous le connaissez déjà,
le taper directement est le plus rapide (évite toute recherche) ;
laissé vide, une recherche automatique sous `$HOME` prend le relais
(reconnue par la présence d'`omega-serv.sh`, quelques secondes) — un
seul candidat trouvé, il est enregistré automatiquement ; zéro ou
plusieurs, il vous le redemande. Ce chemin est mémorisé dans
`.serv-root` (jamais commité) : vous n'avez ensuite jamais besoin de
le retaper.

**Mise à jour.** Depuis le dossier parent, extrayez l'archive par-dessus le dossier existant (`tar -xzf omega-jail.tar.gz`, sans la garde « Déjà extrait » ci-dessus), puis relancez `./install.sh` : le chemin d'omega-serv déjà enregistré est conservé. Si le catalogue contient de nouveaux jails applicables (par exemple les jails RIPOSTE de la 1.1.0), ils sont listés puis installés après confirmation (`sudo`). Un jail déjà installé dont la version diffère du catalogue (règle corrigée, réseaux jamais bannis changés) est listé « (mise à jour) » et remplacé dans la même confirmation, l'ancien fichier étant gardé en `.bak` ; un jail à jour n'est jamais touché. Tant qu'il n'est pas mis à jour, un jail garde son ancien comportement : l'aperçu `./omega-jail.sh` le signale « A METTRE A JOUR », et `./omega-jail.sh --apply --update` le remplace à tout moment. Omega-Fire les affiche ensuite automatiquement, sans autre réglage.

## Utilisation

Dry-run par défaut — n'écrit jamais rien tant que `--apply` n'est pas
explicitement demandé. Aucun chemin à taper : omega-serv est celui
enregistré par `install.sh`, et les jails doivent toujours aller dans
le VRAI dossier fail2ban de la machine — `/etc/fail2ban/` est donc
aussi détecté et vérifié automatiquement :

```bash
./omega-jail.sh
```

Installation réelle (nécessite root — écriture sous `/etc/fail2ban/`,
rechargement de `fail2ban-client`) :

```bash
./omega-jail.sh --apply
```

Si `/etc/fail2ban/` n'existe pas (fail2ban non installé), la commande
échoue proprement avec un message clair plutôt que d'écrire ailleurs
par erreur.

Options utiles :
- `--serv-root` : prend en argument le chemin d'un autre omega-serv à
  cibler ponctuellement, au lieu de celui enregistré par `install.sh`.
- `--jail-d-dir`, `--filter-d-dir`, `--action-d-dir` : prennent chacune
  en argument un chemin de répertoire, à préciser seulement si
  fail2ban n'est pas installé à l'emplacement standard.
- `--only` : prend en argument le nom d'un jail du catalogue, pour
  n'en installer qu'une seule entrée (`--only riposte-7d` : la jail
  RIPOSTE de 7 jours de chaque instance).
- `--force` : écrase un fichier `jail.d/` déjà présent pour un jail du
  catalogue (sans cette option, une collision de nom de fichier est
  toujours signalée et jamais écrasée silencieusement).
- `--update` : remplace les jails d'omega-jail déjà installés dont la
  version diffère du catalogue (ancien fichier gardé en `.bak`) ; un
  jail à jour n'est pas touché.
- `--tailscale-cidr` : prend en argument une plage réseau au format
  CIDR à considérer comme Tailscale, si différente de `100.64.0.0/10`.
- `--serv-config` : prend en argument un chemin, à préciser seulement
  si la config d'omega-serv ne se trouve pas à l'emplacement standard
  (`config/omega-serve.json` sous le chemin omega-serv utilisé).

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
