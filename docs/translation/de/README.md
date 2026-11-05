<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="384">
</div>

# 🔒 OMEGA-JAIL

**Fail2ban-Jail-Paket, kompatibel mit Omega-serv, Omega-Fire und Omega-Waf**

> Entwickelt von [kraynux](https://github.com/kraynux) für [Omega-Server](https://kraynux.snake-mackarel.ts.net)   

Offizielle Seite: [OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**Sprachen:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

Vorkonfigurierter Katalog von [fail2ban](https://www.fail2ban.org/)-Jails
für `omega-serv` und `omega-waf`.
Statt jede Jail von Hand in omega-fire anzulegen, erkennt ein einziger
Befehl Ihre tatsächliche omega-serv-Installation und installiert einen
vollständigen, stimmigen Katalog – unter Beachtung alles Vorhandenen.

Omega-Jail ersetzt nichts: omega-fire bleibt das einzige Werkzeug für
die tägliche Überwachung, Auflistung und Entsperrung; omega-serv und
omega-waf bleiben unverändert. Omega-Jail legt lediglich einmal und
idempotent die Standarddateien von fail2ban ab (`filter.d/`, `jail.d/`).

## Warum eine Netzwerksperre zusätzlich zu den Anwendungssperren?

omega-serv (nativer WAF, Active Defense) und omega-waf (magnet-Skript)
können eine Anfrage bereits auf HTTP-Ebene blockieren und mit `451`
antworten. Diese Sperre auf Anwendungsebene kostet aber noch eine
Verbindung bzw. einen Thread. Omega-Jail überträgt dieselben
Entscheidungen auf die Netzwerkebene (nftables, über fail2ban): Die
Verbindung wird abgewiesen, bevor sie omega-serv überhaupt erreicht,
auf allen Ports – eine Ergänzung im Sinne der gestaffelten Verteidigung,
kein Duplikat.

**Ausnahme: Tailscale.** Hinter einem Tailscale-Tunnel greift die
nftables-Regel, die vertrauenswürdigen Verkehr zulässt, immer vor der
Regel, die fail2ban zum Sperren einfügt – die Netzwerksperre bleibt für
diese Clients wirkungslos. Jede Jail des Katalogs enthält daher eine
Brücke: Fällt die gesperrte IP in den Tailscale-Bereich (standardmäßig
`100.64.0.0/10`), wird die Sperre an die native Blocklist von omega-serv
weitergereicht, die dann ausdrücklich mit `451` antwortet – der
Unterschied „gesperrt/nicht gesperrt“ bleibt auch über Tailscale
sichtbar. Diese Brücke ist immer *fail-open*: Ein Fehler hier
(omega-serv fehlt, Konfiguration nicht gefunden) lässt die normale
Netzwerksperre für alle anderen nie scheitern.

**Hinter einem lokalen Proxy (Tailscale Funnel, Reverse Proxy auf derselben Maschine).** Die Verbindungen kommen dann vom lokalen Host: Die Netzwerksperre erreicht den Besucher nie. Omega-Jail erkennt das (vertrauenswürdiger Proxy von omega-serv, der `127.0.0.1` oder `::1` abdeckt), und die Brücke reicht dann jede Sperre einer öffentlichen Adresse an die Blocklist von omega-serv weiter, die mit `451` antwortet — derselbe Weg wie beim Magnet-Skript. Die RIPOSTE-Jails werden nicht weitergereicht: RIPOSTE hat seine lokale Sperre bereits gesetzt.

**Nie gesperrte Netze.** Nur externer Verkehr kann gesperrt werden: der lokale Host, Tailscale (`100.64.0.0/10`) und das lokale Netz nie. Jede erzeugte Jail erhält eine `ignoreip`-Zeile mit der **von omega-serv selbst gelieferten** Liste (`omega-serv waf never-auto-block`, Einstellung `options.waf.reputation.never_auto_block`) – nie eine fest eingetragene Kopie. Ein bereits in `[DEFAULT]` gesetztes `ignoreip` wird beibehalten und ergänzt, nie überschrieben. Die Tailscale-Brücke reicht nie die Sperre einer ausgenommenen Adresse weiter: Mit den Standardeinstellungen reicht sie also nichts mehr weiter (Ihre externen Besucher kommen mit ihrer echten öffentlichen Adresse). Außer hinter einem lokalen Proxy: siehe vorigen Absatz. Ist omega-serv nicht auffindbar oder zu alt, wird nur der lokale Host ausgenommen, mit einer Warnung im Bericht. Eine bestehende Installation wird nur mit `--apply --force` aktualisiert.

## Katalog

**10 Jails**: 6 Basis-Jails, einmal installiert, und 4 RIPOSTE-Jails, für **jede** omega-serv-Instanz installiert (mit dem Namen ihres Dienstes als Präfix, z. B. `omega-serv-riposte-1h`).

| Jail | Quelle | Auslöser |
|---|---|---|
| `omega-waf-blocklist-sync` | Blocklist des omega-waf-magnet-Skripts | jede bereits vom Skript gesperrte IP |
| `omega-waf-magnet-alerts` | Warnungen des omega-waf-magnet-Skripts | 3 Warnungen / 5 min (gleiche Schwelle wie die Autosperre des Skripts) |
| `omega-serv-waf-block` | Warnungen des nativen WAF von omega-serv | 3 echte Blockierungen / 10 min (nie bei `log-only`) |
| `omega-serv-active-defense` | angereichertes Active-Defense-Protokoll | 2 Anfragen `hostile`/`contained` / 15 min |
| `omega-serv-auth-bruteforce` | Zugriffsprotokoll von omega-serv | 5 Antworten `401` / 5 min |
| `omega-serv-scan` | Zugriffsprotokoll von omega-serv | 15 Antworten `404` / 2 min |
| `<service>-riposte-1h` | Netzwerksperren von RIPOSTE (omega-serv 2.1.0), ein Satz pro Instanz | Stufen von 1 h bis unter 6 h: Sperre von 1 h |
| `<service>-riposte-6h` | Netzwerksperren von RIPOSTE (omega-serv 2.1.0), ein Satz pro Instanz | Stufen von 6 h bis unter 24 h: Sperre von 6 h |
| `<service>-riposte-24h` | Netzwerksperren von RIPOSTE (omega-serv 2.1.0), ein Satz pro Instanz | Stufen von 24 h bis unter 7 Tagen: Sperre von 24 h |
| `<service>-riposte-7d` | Netzwerksperren von RIPOSTE (omega-serv 2.1.0), ein Satz pro Instanz | Stufen ab 7 Tagen: Sperre von 7 Tagen |

Jede Jail wird nur installiert, wenn die zugehörige Quelle auf Seiten
von omega-serv tatsächlich eingerichtet ist (nativer WAF aktiviert,
Active Defense aktiviert, Extra `magnet` eingerichtet, RIPOSTE mit
Netzwerksperre aktiviert) – andernfalls wird sie als nicht anwendbar
gemeldet und nie blind angelegt.

**RIPOSTE-Jails (seit 1.1.0).** RIPOSTE, das Modul für abgestufte
Reaktionen von omega-serv 2.1.0, schreibt jede seiner Netzwerksperren
in sein Protokoll; Omega-Jail installiert vier Jails mit fester Dauer
(1 h, 6 h, 24 h, 7 Tage), und jede RIPOSTE-Stufe geht an die längste,
die sie nicht überschreitet. Alle omega-serv-Instanzen der Maschine
werden automatisch erkannt (systemd-Dienste und Instanzregister): Jede
erhält eigene Jails, mit ihrem Dienstnamen als Präfix.

## Installation

```bash
[ -d omega-jail ] && echo "ℹ️ Bereits hier entpackt, Schritt übersprungen." || tar -xzf omega-jail.tar.gz
cd omega-jail/
chmod +x install.sh
./install.sh
```

`install.sh` legt die virtuelle Umgebung an, installiert omega-jail
(`pip install -e .`, für diesen Schritt sind keine Root-Rechte nötig),
macht `omega-jail.sh`/`install.sh` ausführbar – und fragt dann nach dem
Pfad der zu schützenden omega-serv-Installation: Kennen Sie ihn bereits,
ist direktes Eintippen am schnellsten (keine Suche); bleibt das Feld
leer, übernimmt eine automatische Suche unter `$HOME` (erkannt am
Vorhandensein von `omega-serv.sh`, wenige Sekunden) – ein einziger
Treffer wird automatisch gespeichert; bei keinem oder mehreren wird
erneut gefragt. Der Pfad wird in `.serv-root` gespeichert (nie
committet): Sie müssen ihn danach nie wieder eingeben.

**Aktualisierung.** Entpacken Sie das Archiv aus dem übergeordneten Ordner über den bestehenden Ordner (`tar -xzf omega-jail.tar.gz`, ohne die Schutzabfrage „Bereits entpackt“ oben) und starten Sie `./install.sh` erneut: Der bereits gespeicherte omega-serv-Pfad bleibt erhalten. Enthält der Katalog neue anwendbare Jails (zum Beispiel die RIPOSTE-Jails der 1.1.0), werden sie aufgelistet und nach Bestätigung (`sudo`) installiert; bereits installierte Jails werden nie verändert. Omega-Fire zeigt sie danach automatisch an, ohne weitere Einstellung.

## Verwendung

Standardmäßig Probelauf (dry-run) – es wird nichts geschrieben, solange
`--apply` nicht ausdrücklich angegeben ist. Kein Pfad einzutippen:
omega-serv ist der von `install.sh` gespeicherte, und die Jails müssen
immer in das ECHTE fail2ban-Verzeichnis der Maschine – `/etc/fail2ban/`
wird daher ebenfalls automatisch erkannt und geprüft:

```bash
./omega-jail.sh
```

Echte Installation (erfordert Root – schreibt unter `/etc/fail2ban/`,
lädt `fail2ban-client` neu):

```bash
./omega-jail.sh --apply
```

Existiert `/etc/fail2ban/` nicht (fail2ban nicht installiert), bricht
der Befehl sauber mit einer klaren Meldung ab, statt versehentlich
woanders hinzuschreiben.

Nützliche Optionen:
- `--serv-root`: nimmt den Pfad eines anderen omega-serv, um ihn
  einmalig anzusteuern, statt des von `install.sh` gespeicherten.
- `--jail-d-dir`, `--filter-d-dir`, `--action-d-dir`: nehmen je einen
  Verzeichnispfad, nur nötig, wenn fail2ban nicht am Standardort
  installiert ist.
- `--only`: nimmt den Namen einer Katalog-Jail, um nur diesen einen
  Eintrag zu installieren (`--only riposte-7d`: die 7-Tage-RIPOSTE-Jail
  jeder Instanz).
- `--force`: überschreibt eine bereits vorhandene `jail.d/`-Datei einer
  Katalog-Jail (ohne diese Option wird eine Dateinamenkollision immer
  gemeldet und nie stillschweigend überschrieben).
- `--tailscale-cidr`: nimmt einen Netzbereich im CIDR-Format, der als
  Tailscale gelten soll, falls abweichend von `100.64.0.0/10`.
- `--serv-config`: nimmt einen Pfad, nur nötig, wenn die Konfiguration
  von omega-serv nicht am Standardort liegt (`config/omega-serve.json`
  unter dem verwendeten omega-serv-Pfad).

Jeder Lauf kann gefahrlos wiederholt werden: Eine bereits von einem
früheren Lauf angelegte Jail (oder jede externe Jail, die dieselbe
Protokolldatei bereits überwacht, egal unter welchem Namen) wird
automatisch erkannt und übersprungen, nie dupliziert.

## Voraussetzungen

- `fail2ban` installiert (`fail2ban-client` muss im `PATH` liegen).
- Eine bestehende, eingerichtete omega-serv-Installation (nativer WAF,
  Active Defense und/oder das Extra `magnet` müssen auf Seiten von
  omega-serv aktiviert sein, damit die zugehörigen Jails anwendbar
  werden).

## Lizenz

Veröffentlicht unter der MIT-Lizenz. Siehe die Datei [LICENSE](../../../LICENSE).
