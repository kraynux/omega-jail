# Changelog

Format inspiré de [Keep a Changelog](https://keepachangelog.com/).

## [1.2.1] — construite le 2026-11-10, non publiée

Correctifs issus de l'étude de l'interconnecteur de la suite (`~/DEV/CONNECT/`), étapes 1 et 2.

### Ajouté

- **Jeton d'installation** `var/omega-jeton.json` (étape 2) : `./omega-jail.sh synchro jeton`, lancé par
  `install.sh`, dit au futur omega-connect qu'Omega-Jail est installé, où, et dans quelle version. Écrit sous
  votre compte (jamais en root, sans bannière ni sudo), même format que les autres outils omega, exclu de
  l'archive. Omega-Jail n'a pas de fiche : ce qu'il installe appartient à fail2ban et y est lu directement.

### Corrigé

- **`--apply` remet les droits de tout ce qu'il pose** (lot E de l'étape 3, `omega-connect reparer`) : les
  fichiers `omega-*` de `jail.d`, `filter.d` et `action.d` repassent en root:root 0644, le dossier et le script
  du pont en root:root 0755, même quand leur contenu n'a pas changé. Avant, `--apply --update` réécrivait le
  contenu mais gardait les droits : un fichier passé en 0666 ou repris par un autre compte restait tel quel.
  Un lien symbolique n'est jamais suivi.
- **Le pont n'est plus exécuté depuis le dossier d'Omega-Jail.** fail2ban (root) lançait
  `<omega-jail>/.venv/bin/omega-jail-tailscale-bridge`, un code modifiable par l'utilisateur, et supprimer
  Omega-Jail cassait le pont sans le dire. `--apply` installe maintenant une copie autonome, appartenant à
  root, dans `/usr/local/lib/omega-jail/` (option `--bridge-dir`), lancée avec le Python du système.
- **Une action du pont par instance omega-serv** (`omega-jail-tailscale-bridge-<service>`) : avec une seule
  action pour toute la machine, les jails RIPOSTE de l'instance B relayaient vers la blocklist, la liste
  protégée et le réglage `relay_all` de l'instance principale.
- **Le pont ne lève plus un ban qu'il n'a pas posé.** Il marque ses bans de l'origine `omega-jail:<jail>`
  et les lève en une seule opération conditionnelle (`blocklist remove --origin`, omega-serv 2.6.1+). Avant,
  la lecture puis le retrait étaient séparés : un ban posé entre-temps par le WAF ou RIPOSTE pouvait être
  levé. Le ban plus long d'un autre jail du pont n'est plus remplacé par un plus court (ni levé à sa place).
  Avec un omega-serv plus ancien, l'ancien comportement s'applique.
- **Lecture de la blocklist en JSON** (`blocklist list --format json`, omega-serv 2.6.1+) au lieu de la
  sortie texte traduite.
- **Journal recréé pour un jail déjà installé** : un journal supprimé depuis l'installation n'était jamais
  recréé (jail identique au catalogue), alors que fail2ban entier refuse de redémarrer sans lui.
- **`omega-jail.sh` ne lance plus `pip install` en root** dans le dossier de l'utilisateur : un environnement
  incomplet demande de relancer `install.sh` sans sudo.

## [1.2.0] — 2026-11-09

### Ajouté

- **Contact et support en ligne de commande** (omega-jail n'a pas d'interface ; même fonction que l'écran
  « Contact et support » d'omega-serv et des autres outils omega) :
  - `omega-jail contact` : payer un café (page PayPal), contacter le support (mail et formulaire de
    contact du site, aucun mail envoyé par omega-jail), comment se déclarer ;
  - `omega-jail declaration status | declare [--continent X] [--pays Y] [--yes] | withdraw [--yes]` :
    déclaration anonyme **une seule fois** (clé tirée au hasard, nom et version, continent et pays
    facultatifs). Sans `--yes`, rien n'est envoyé : le message exact est seulement affiché. Rien n'est
    enregistré si la réception est injoignable ; le retrait supprime l'entrée à la réception et la clé
    locale (`var/declaration.json`, jamais livrée dans l'archive) ;
  - `omega-jail version [--check]` : version installée ; `--check` la compare à la liste publiée sur
    le site (`download/sha.txt`), rien n'est envoyé.
- README ×17 : section « Contact et support ».

### Modifié

- Publication alignée sur les autres outils omega : archive versionnée
  `download/omega-jail-1.2.0.tar.gz` et `download/sha.txt` (lus par `version --check`).

