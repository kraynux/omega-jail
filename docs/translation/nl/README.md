<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="384">
</div>

# 🔒 OMEGA-JAIL

**Fail2ban-jailpakket, compatibel met Omega-serv, Omega-Fire en Omega-Waf**

> Ontwikkeld door [kraynux](https://github.com/kraynux) voor [Omega-Server](https://kraynux.snake-mackarel.ts.net)   

Officiële pagina: [OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**Talen:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

Vooraf ingestelde catalogus van [fail2ban](https://www.fail2ban.org/)-jails
voor `omega-serv` en `omega-waf`.
In plaats van elke jail met de hand in omega-fire aan te maken,
herkent één opdracht uw echte omega-serv-installatie en installeert
een volledige, samenhangende catalogus, met respect voor alles wat al
bestaat.

Omega-Jail vervangt niets: omega-fire blijft het enige hulpmiddel voor
dagelijks bewaken, opsommen en deblokkeren; omega-serv en omega-waf
blijven ongewijzigd. Omega-Jail plaatst alleen eenmalig en idempotent de
standaardbestanden van fail2ban (`filter.d/`, `jail.d/`).

## Waarom een netwerkban naast de applicatiebans?

omega-serv (eigen WAF, Active Defense) en omega-waf (magnet-script)
kunnen een verzoek al op HTTP-niveau blokkeren en met `451` antwoorden.
Die blokkade op applicatieniveau kost nog steeds een verbinding/een
thread. Omega-Jail brengt dezelfde beslissingen naar het netwerkniveau
(nftables, via fail2ban): de verbinding wordt geweigerd nog vóór ze
omega-serv bereikt, op alle poorten — een aanvulling in gelaagde
verdediging, geen dubbel werk.

**Uitzondering: Tailscale.** Achter een Tailscale-tunnel komt de
nftables-regel die vertrouwd verkeer toelaat altijd vóór de regel die
fail2ban invoegt om te bannen — de netwerkban heeft dan geen effect
voor deze clients. Elke jail van de catalogus bevat daarom een brug:
valt het gebande IP binnen het Tailscale-bereik (standaard
`100.64.0.0/10`), dan wordt de ban doorgegeven aan de eigen blocklist
van omega-serv, die dan expliciet `451` antwoordt — het onderscheid
"geband/niet geband" blijft ook via Tailscale zichtbaar. Deze brug is
altijd *fail-open*: een fout hier (omega-serv afwezig, configuratie
niet gevonden) laat de gewone netwerkban voor alle anderen nooit
mislukken.

**Achter een lokale proxy (Tailscale Funnel, reverse proxy op dezelfde machine).** De verbindingen komen dan van de lokale host: de netwerkban bereikt de bezoeker nooit. Omega-Jail detecteert dat (vertrouwde proxy van omega-serv die `127.0.0.1` of `::1` dekt) en de brug geeft dan elke ban van een publiek adres door aan de blocklist van omega-serv, die met `451` antwoordt — hetzelfde circuit als het magnet-script. De RIPOSTE-jails worden niet doorgegeven: RIPOSTE heeft zijn lokale ban al gezet.

**Netwerken die nooit geband worden.** Alleen extern verkeer kan geband worden: de lokale host, Tailscale (`100.64.0.0/10`) en het lokale netwerk nooit. Elke gegenereerde jail krijgt een regel `ignoreip` met de lijst **die omega-serv zelf levert** (`omega-serv waf never-auto-block`, instelling `options.waf.reputation.never_auto_block`) — nooit een vaste kopie hier. Een `ignoreip` die al in `[DEFAULT]` staat, blijft behouden en wordt aangevuld, nooit overschreven. De Tailscale-brug geeft de ban van een vrijgesteld adres nooit door: met de standaardinstellingen geeft ze dus niets meer door (uw externe bezoekers komen binnen met hun echte publieke adres). Behalve achter een lokale proxy: zie de vorige alinea. Is omega-serv niet te vinden of te oud, dan is alleen de lokale host vrijgesteld, met een waarschuwing in het rapport. Een bestaande installatie wordt alleen bijgewerkt met `--apply --force`.

## Catalogus

**10 jails**: 6 basisjails, één keer geïnstalleerd, en 4 RIPOSTE-jails, geïnstalleerd voor **elke** omega-serv-instantie (met de naam van zijn service als voorvoegsel, bv. `omega-serv-riposte-1h`).

| Jail | Bron | Aanleiding |
|---|---|---|
| `omega-waf-blocklist-sync` | blocklist van het omega-waf-magnet-script | elk IP dat het script al geband heeft |
| `omega-waf-magnet-alerts` | meldingen van het omega-waf-magnet-script | 3 meldingen / 5 min (dezelfde drempel als de auto-ban van het script) |
| `omega-serv-waf-block` | meldingen van de eigen WAF van omega-serv | 3 echte blokkades / 10 min (nooit bij `log-only`) |
| `omega-serv-active-defense` | verrijkt Active Defense-logboek | 2 verzoeken `hostile`/`contained` / 15 min |
| `omega-serv-auth-bruteforce` | toegangslog van omega-serv | 5 antwoorden `401` / 5 min |
| `omega-serv-scan` | toegangslog van omega-serv | 15 antwoorden `404` / 2 min |
| `<service>-riposte-1h` | netwerkbans van RIPOSTE (omega-serv 2.1.0), één set per instantie | niveaus van 1 u tot minder dan 6 u: ban van 1 u |
| `<service>-riposte-6h` | netwerkbans van RIPOSTE (omega-serv 2.1.0), één set per instantie | niveaus van 6 u tot minder dan 24 u: ban van 6 u |
| `<service>-riposte-24h` | netwerkbans van RIPOSTE (omega-serv 2.1.0), één set per instantie | niveaus van 24 u tot minder dan 7 dagen: ban van 24 u |
| `<service>-riposte-7d` | netwerkbans van RIPOSTE (omega-serv 2.1.0), één set per instantie | niveaus van 7 dagen of meer: ban van 7 dagen |

Elke jail wordt alleen geïnstalleerd als de bijbehorende bron in
omega-serv echt is ingesteld (eigen WAF aan, Active Defense aan, extra
`magnet` ingesteld, RIPOSTE aan met netwerkban) — anders wordt hij als
niet van toepassing gemeld en nooit blind aangemaakt.

**RIPOSTE-jails (sinds 1.1.0).** RIPOSTE, de module voor getrapte
reacties van omega-serv 2.1.0, schrijft elk van zijn netwerkbans in
zijn logboek; Omega-Jail installeert vier jails met vaste duur (1 u,
6 u, 24 u, 7 dagen) en elke trede van RIPOSTE gaat naar de langste die
haar niet overschrijdt. Alle omega-serv-instanties op de machine worden
automatisch herkend (systemd-diensten en instantieregister): elk krijgt
eigen jails, met de naam van zijn dienst als voorvoegsel.

## Installatie

```bash
[ -d omega-jail ] && echo "ℹ️ Hier al uitgepakt, stap overgeslagen." || tar -xzf omega-jail.tar.gz
cd omega-jail/
chmod +x install.sh
./install.sh
```

`install.sh` maakt de virtuele omgeving aan, installeert omega-jail
(`pip install -e .`, geen rootrechten nodig voor deze stap), maakt
`omega-jail.sh`/`install.sh` uitvoerbaar — en vraagt dan het pad van de
te beschermen omega-serv-installatie: kent u het al, dan is het direct
intypen het snelst (geen zoektocht); laat u het leeg, dan neemt een
automatische zoektocht onder `$HOME` het over (herkend aan de
aanwezigheid van `omega-serv.sh`, enkele seconden) — één gevonden
kandidaat wordt automatisch opgeslagen; geen of meerdere, dan vraagt hij
het opnieuw. Het pad wordt bewaard in `.serv-root` (nooit gecommit): u
hoeft het daarna nooit meer in te typen.

**Bijwerken.** Pak vanuit de bovenliggende map het archief uit over de bestaande map (`tar -xzf omega-jail.tar.gz`, zonder de controle „Al uitgepakt” hierboven) en voer `./install.sh` opnieuw uit: het al opgeslagen omega-serv-pad blijft behouden. Bevat de catalogus nieuwe toepasbare jails (bijvoorbeeld de RIPOSTE-jails van 1.1.0), dan worden ze opgesomd en na bevestiging (`sudo`) geïnstalleerd; al geïnstalleerde jails worden nooit aangeraakt. Omega-Fire toont ze daarna automatisch, zonder verdere instelling.

## Gebruik

Standaard een proefdraai (dry-run) — er wordt niets geschreven zolang
`--apply` niet uitdrukkelijk gevraagd wordt. Geen pad om in te typen:
omega-serv is het pad dat `install.sh` bewaarde, en de jails moeten
altijd in de ECHTE fail2ban-map van de machine — ook `/etc/fail2ban/`
wordt dus automatisch herkend en gecontroleerd:

```bash
./omega-jail.sh
```

Echte installatie (vereist root — schrijft onder `/etc/fail2ban/`,
herlaadt `fail2ban-client`):

```bash
./omega-jail.sh --apply
```

Bestaat `/etc/fail2ban/` niet (fail2ban niet geïnstalleerd), dan stopt
de opdracht netjes met een duidelijke melding in plaats van per vergissing
ergens anders te schrijven.

Handige opties:
- `--serv-root`: krijgt het pad van een andere omega-serv om eenmalig
  te gebruiken, in plaats van het pad dat `install.sh` bewaarde.
- `--jail-d-dir`, `--filter-d-dir`, `--action-d-dir`: krijgen elk een
  mappad, alleen nodig als fail2ban niet op de standaardplek staat.
- `--only`: krijgt de naam van een jail uit de catalogus, om alleen die
  ene te installeren (`--only riposte-7d`: de RIPOSTE-jail van 7 dagen
  van elke instantie).
- `--force`: overschrijft een bestaand `jail.d/`-bestand van een jail
  uit de catalogus (zonder deze optie wordt een botsing van
  bestandsnamen altijd gemeld en nooit stilzwijgend overschreven).
- `--tailscale-cidr`: krijgt een netwerkbereik in CIDR-notatie dat als
  Tailscale geldt, als het afwijkt van `100.64.0.0/10`.
- `--serv-config`: krijgt een pad, alleen nodig als de configuratie van
  omega-serv niet op de standaardplek staat (`config/omega-serve.json`
  onder het gebruikte omega-serv-pad).

Elke uitvoering kan veilig herhaald worden: een jail die een eerdere
uitvoering al aanmaakte (of elke externe jail die hetzelfde logbestand
al bewaakt, onder welke naam ook) wordt automatisch herkend en
overgeslagen, nooit verdubbeld.

## Vereisten

- `fail2ban` geïnstalleerd (`fail2ban-client` moet in het `PATH` staan).
- Een bestaande, ingestelde omega-serv-installatie (eigen WAF, Active
  Defense en/of het extra `magnet` moeten in omega-serv aan staan
  voordat de bijbehorende jails van toepassing worden).

## Licentie

Verspreid onder de MIT-licentie. Zie het bestand [LICENSE](../../../LICENSE).
