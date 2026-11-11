<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="512">
</div>

# 🔒 OMEGA-JAIL

**Pacchetto di jail Fail2ban compatibile con Omega-serv, Omega-Fire e Omega-Waf**

> Sviluppato da [kraynux](https://github.com/kraynux) per [Omega-Server](https://kraynux.snake-mackarel.ts.net)   

Pagina ufficiale: [OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**Lingue:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

Catalogo preconfigurato di jail [fail2ban](https://www.fail2ban.org/)
per `omega-serv` e `omega-waf`.
Invece di creare ogni jail a mano in omega-fire, un solo comando
rileva la vostra installazione reale di omega-serv e installa un
catalogo completo e coerente, rispettando tutto ciò che esiste già.

Omega-Jail non sostituisce nulla: omega-fire resta l'unico strumento
che sorveglia, elenca e sblocca ogni giorno; omega-serv e omega-waf
restano invariati. Omega-Jail si limita a depositare una volta, in modo
idempotente, i file standard di fail2ban (`filter.d/`, `jail.d/`).

## Perché un ban di rete oltre ai ban applicativi?

omega-serv (WAF nativo, Active Defense) e omega-waf (script magnet)
sanno già bloccare una richiesta a livello HTTP e rispondere `451`.
Questo blocco applicativo costa comunque una connessione/un thread.
Omega-Jail porta le stesse decisioni a livello di rete (nftables,
tramite fail2ban): la connessione viene rifiutata prima ancora di
raggiungere omega-serv, su tutte le porte — un complemento di difesa in
profondità, non un doppione.

**Eccezione: Tailscale.** Dietro un tunnel Tailscale, la regola
nftables che accetta il traffico fidato viene sempre prima di quella
che fail2ban inserisce per bannire — il ban di rete diventa inefficace
per questi client. Ogni jail del catalogo include quindi un ponte: se
l'IP bannito rientra nell'intervallo Tailscale (`100.64.0.0/10` per
impostazione predefinita), il ban viene inoltrato alla blocklist nativa
di omega-serv, che risponde allora con un `451` esplicito — la
distinzione "bannito/non bannito" resta visibile anche tramite
Tailscale. Questo ponte è sempre *fail-open*: un errore qui (omega-serv
assente, configurazione non trovata) non fa mai fallire il ban di rete
normale per tutti gli altri.

**Dietro un proxy locale (Tailscale Funnel, reverse proxy sulla stessa macchina).** Le connessioni arrivano allora dall'host locale: il ban di rete non raggiunge mai il visitatore. Omega-Jail lo rileva (proxy fidato di omega-serv che copre `127.0.0.1` o `::1`) e il ponte inoltra allora ogni ban di un indirizzo pubblico alla blocklist di omega-serv, che risponde `451` — lo stesso circuito dello script magnet. Le jail di RIPOSTE non vengono inoltrate: RIPOSTE ha già applicato il suo ban locale.

**Dove gira il ponte.** `--apply` installa una copia autonoma del ponte, di proprietà di root, in `/usr/local/lib/omega-jail/` (opzione `--bridge-dir`), avviata con il Python di sistema: fail2ban non esegue più codice che si trova nella cartella di Omega-Jail, e cancellare quella cartella non rompe più il ponte. Ogni istanza di omega-serv ha la propria azione (`omega-jail-tailscale-bridge-<service>`), che inoltra alla **sua** blocklist. Il ponte marca i suoi ban con l'origine `omega-jail:<jail>` e revoca solo i propri, in un'unica operazione (omega-serv 2.6.1 o successivo; altrimenti, comportamento precedente).

**Reti mai bannite.** Solo il traffico esterno può essere bannito: l'host locale, Tailscale (`100.64.0.0/10`) e la rete locale non lo sono mai. Ogni jail generata riceve una riga `ignoreip` con l'elenco **fornito da omega-serv stesso** (`omega-serv waf never-auto-block`, impostazione `options.waf.reputation.never_auto_block`) — mai una copia scritta a mano qui. Un `ignoreip` già definito in `[DEFAULT]` viene conservato e completato, mai sovrascritto. Il ponte Tailscale non inoltra mai il ban di un indirizzo esentato: con le impostazioni predefinite non inoltra quindi più nulla (i vostri visitatori esterni arrivano con il loro vero indirizzo pubblico). Tranne dietro un proxy locale: vedi il paragrafo precedente. Se omega-serv è introvabile o troppo vecchio, è esentato solo l'host locale, con un avviso nel rapporto. Un'installazione esistente viene aggiornata solo con `--apply --force`.

## Catalogo

**10 jail**: 6 jail di base, installate una sola volta, e 4 jail RIPOSTE, installate per **ogni** istanza di omega-serv (con il nome del suo servizio come prefisso, es. `omega-serv-riposte-1h`).

| Jail | Sorgente | Attivazione |
|---|---|---|
| `omega-waf-blocklist-sync` | blocklist dello script magnet omega-waf | ogni IP già bannito dallo script |
| `omega-waf-magnet-alerts` | avvisi dello script magnet omega-waf | 3 avvisi / 5 min (stessa soglia dell'auto-ban dello script) |
| `omega-serv-waf-block` | avvisi del WAF nativo di omega-serv | 3 blocchi reali / 10 min (mai su `log-only`) |
| `omega-serv-active-defense` | registro arricchito di Active Defense | 2 richieste `hostile`/`contained` / 15 min |
| `omega-serv-auth-bruteforce` | log di accesso di omega-serv | 5 risposte `401` / 5 min |
| `omega-serv-scan` | log di accesso di omega-serv | 15 risposte `404` / 2 min |
| `<service>-riposte-1h` | ban di rete di RIPOSTE (omega-serv 2.1.0), una serie per istanza | livelli da 1 h a meno di 6 h: ban di 1 h |
| `<service>-riposte-6h` | ban di rete di RIPOSTE (omega-serv 2.1.0), una serie per istanza | livelli da 6 h a meno di 24 h: ban di 6 h |
| `<service>-riposte-24h` | ban di rete di RIPOSTE (omega-serv 2.1.0), una serie per istanza | livelli da 24 h a meno di 7 giorni: ban di 24 h |
| `<service>-riposte-7d` | ban di rete di RIPOSTE (omega-serv 2.1.0), una serie per istanza | livelli di 7 giorni o più: ban di 7 giorni |

Ogni jail viene installata solo se la sorgente corrispondente è
realmente configurata in omega-serv (WAF nativo attivato, Active
Defense attivato, extra `magnet` configurato, RIPOSTE attivato con il
ban di rete) — altrimenti viene segnalata come non applicabile, mai
creata alla cieca.

**Jail RIPOSTE (dalla 1.1.0).** RIPOSTE, il modulo di risposta graduale
di omega-serv 2.1.0, scrive ciascuno dei suoi ban di rete nel proprio
registro; Omega-Jail installa quattro jail di durata fissa (1 h, 6 h,
24 h, 7 giorni) e ogni livello di RIPOSTE va alla più lunga che non lo
supera. Tutte le istanze di omega-serv della macchina vengono rilevate
automaticamente (servizi systemd e registro delle istanze): ognuna
riceve le proprie jail, con il nome del suo servizio come prefisso.

## Installazione

```bash
[ -d omega-jail ] && echo "ℹ️ Già estratto qui, passaggio saltato." || tar -xzf omega-jail.tar.gz
cd omega-jail/
chmod +x install.sh
./install.sh
```

`install.sh` crea l'ambiente virtuale, installa omega-jail
(`pip install -e .`, nessun privilegio root necessario per questo
passaggio), rende eseguibili `omega-jail.sh`/`install.sh` — poi chiede
il percorso dell'installazione omega-serv da proteggere: se lo
conoscete già, digitarlo direttamente è la via più rapida (nessuna
ricerca); lasciato vuoto, subentra una ricerca automatica sotto `$HOME`
(riconosciuta dalla presenza di `omega-serv.sh`, pochi secondi) — un
solo candidato trovato viene salvato automaticamente; nessuno o più di
uno, ve lo richiede. Il percorso viene memorizzato in `.serv-root` (mai
inviato al repository): non dovrete più ridigitarlo.

**Aggiornamento.** Dalla cartella superiore, estrai l'archivio sopra la cartella esistente (`tar -xzf omega-jail.tar.gz`, senza la protezione «Già estratto» qui sopra), poi riesegui `./install.sh`: il percorso di omega-serv già registrato viene mantenuto. Se il catalogo contiene nuove jail applicabili (ad esempio le jail RIPOSTE della 1.1.0), vengono elencate e poi installate dopo conferma (`sudo`); le jail già installate non vengono mai toccate. Omega-Fire le mostra poi automaticamente, senza altre impostazioni.

## Utilizzo

Prova a vuoto (dry-run) per impostazione predefinita — non scrive mai
nulla finché `--apply` non è richiesto esplicitamente. Nessun percorso
da digitare: omega-serv è quello salvato da `install.sh`, e le jail
devono sempre andare nella VERA cartella fail2ban della macchina —
anche `/etc/fail2ban/` viene quindi rilevato e verificato
automaticamente:

```bash
./omega-jail.sh
```

Installazione reale (richiede root — scrittura sotto `/etc/fail2ban/`,
ricaricamento di `fail2ban-client`):

```bash
./omega-jail.sh --apply
```

Se `/etc/fail2ban/` non esiste (fail2ban non installato), il comando
termina in modo pulito con un messaggio chiaro invece di scrivere
altrove per errore.

Opzioni utili:
- `--serv-root`: riceve il percorso di un altro omega-serv da usare
  una tantum, al posto di quello salvato da `install.sh`.
- `--jail-d-dir`, `--filter-d-dir`, `--action-d-dir`: ricevono ciascuna
  il percorso di una cartella, da indicare solo se fail2ban non è
  installato nella posizione standard.
- `--only`: riceve il nome di una jail del catalogo, per installare
  solo quella voce (`--only riposte-7d`: la jail RIPOSTE di 7 giorni di
  ogni istanza).
- `--force`: sovrascrive un file `jail.d/` già presente per una jail
  del catalogo (senza questa opzione, una collisione di nomi di file
  viene sempre segnalata e mai sovrascritta in silenzio).
- `--tailscale-cidr`: riceve un intervallo di rete in formato CIDR da
  considerare Tailscale, se diverso da `100.64.0.0/10`.
- `--serv-config`: riceve un percorso, da indicare solo se la
  configurazione di omega-serv non si trova nella posizione standard
  (`config/omega-serve.json` sotto il percorso omega-serv usato).

Ogni esecuzione può essere ripetuta senza rischi: una jail già creata
da un'esecuzione precedente (o qualsiasi jail esterna che sorveglia già
lo stesso file di log, con qualunque nome) viene rilevata
automaticamente e saltata, mai duplicata.

## Contatti e supporto

omega-jail non ha interfaccia: la funzione **Contatti e supporto** degli altri strumenti omega passa dalla riga di comando.

```bash
./omega-jail.sh contact                              # caffè (PayPal), e-mail e modulo del supporto
./omega-jail.sh declaration declare --pays FR        # mostra il messaggio esatto, non viene inviato nulla
./omega-jail.sh declaration declare --pays FR --yes
./omega-jail.sh declaration status
./omega-jail.sh declaration withdraw --yes           # non dichiararmi più
./omega-jail.sh version --check                      # ultima versione pubblicata
```

La dichiarazione è volontaria, disattivata per impostazione predefinita e inviata una sola volta: serve solo a contare gli utenti e, se lo si desidera, il loro continente o paese (elenchi chiusi, mai testo libero). Invia una chiave estratta a caso, il nome del software (`omega-jail`) e la sua versione; mai un nome, un nome di macchina, un'impostazione, un obiettivo o un risultato. L'indirizzo IP non viene registrato nelle dichiarazioni, ma, come per ogni visita, passa per i controlli di sicurezza e il registro del server di ricezione. `version --check` legge solo l'elenco delle versioni pubblicate sul sito; non viene inviato nulla.

## Requisiti

- `fail2ban` installato (`fail2ban-client` deve essere nel `PATH`).
- Un'installazione di omega-serv esistente e configurata (WAF nativo,
  Active Defense e/o l'extra `magnet` devono essere attivati in
  omega-serv perché le jail corrispondenti diventino applicabili).

## Licenza

Distribuito con licenza MIT. Vedere il file [LICENSE](../../../LICENSE).
