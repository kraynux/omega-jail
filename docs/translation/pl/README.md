<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="512">
</div>

# 🔒 OMEGA-JAIL

**Pakiet jaili Fail2ban zgodny z Omega-serv, Omega-Fire i Omega-Waf**

> Opracowany przez [kraynux](https://github.com/kraynux) dla [Omega-Server](https://kraynux.snake-mackarel.ts.net)   

Oficjalna strona: [OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**Języki:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

Gotowy katalog jaili [fail2ban](https://www.fail2ban.org/)
dla `omega-serv` i `omega-waf`.
Zamiast tworzyć każdy jail ręcznie w omega-fire, jedno polecenie
wykrywa Twoją rzeczywistą instalację omega-serv i instaluje pełny,
spójny katalog, z poszanowaniem wszystkiego, co już istnieje.

Omega-Jail niczego nie zastępuje: omega-fire pozostaje jedynym
narzędziem do codziennego nadzoru, listowania i odbanowywania;
omega-serv i omega-waf pozostają bez zmian. Omega-Jail jedynie jeden
raz, idempotentnie, umieszcza standardowe pliki fail2ban (`filter.d/`,
`jail.d/`).

## Dlaczego ban sieciowy oprócz banów aplikacyjnych?

omega-serv (natywny WAF, Active Defense) i omega-waf (skrypt magnet)
potrafią już zablokować żądanie na poziomie HTTP i odpowiedzieć `451`.
Taka blokada w aplikacji wciąż kosztuje połączenie/wątek. Omega-Jail
przenosi te same decyzje na poziom sieci (nftables, przez fail2ban):
połączenie jest odrzucane, zanim w ogóle dotrze do omega-serv, na
wszystkich portach — uzupełnienie obrony warstwowej, a nie dublowanie.

**Wyjątek: Tailscale.** Za tunelem Tailscale reguła nftables
przepuszczająca zaufany ruch zawsze działa przed regułą, którą fail2ban
dodaje, by zbanować — ban sieciowy nie działa wtedy dla tych klientów.
Każdy jail katalogu zawiera więc mostek: jeśli zbanowany IP należy do
zakresu Tailscale (domyślnie `100.64.0.0/10`), ban jest przekazywany do
natywnej blocklisty omega-serv, która odpowiada wtedy wyraźnym `451` —
rozróżnienie „zbanowany/niezbanowany” pozostaje widoczne także przez
Tailscale. Mostek jest zawsze *fail-open*: błąd w tym miejscu (brak
omega-serv, nieznaleziona konfiguracja) nigdy nie psuje zwykłego bana
sieciowego dla pozostałych.

**Za lokalnym proxy (Tailscale Funnel, reverse proxy na tej samej maszynie).** Połączenia przychodzą wtedy z lokalnego hosta: ban sieciowy nigdy nie dosięga odwiedzającego. Omega-Jail to wykrywa (zaufane proxy omega-serv obejmujące `127.0.0.1` lub `::1`), a most przekazuje wtedy każdy ban adresu publicznego do blocklisty omega-serv, która odpowiada `451` — ten sam obieg co skrypt magnet. Jaile RIPOSTE nie są przekazywane: RIPOSTE nałożył już swój ban lokalny.

**Gdzie działa most.** `--apply` instaluje samodzielną kopię mostu, należącą do roota, w `/usr/local/lib/omega-jail/` (opcja `--bridge-dir`), uruchamianą systemowym Pythonem: fail2ban nie wykonuje już kodu z katalogu Omega-Jail, a usunięcie tego katalogu nie psuje już mostu. Każda instancja omega-serv ma własną akcję (`omega-jail-tailscale-bridge-<service>`), która przekazuje do **jej** blocklisty. Most oznacza swoje blokady pochodzeniem `omega-jail:<jail>` i zdejmuje tylko własne, w jednej operacji (omega-serv 2.6.1 lub nowszy; w przeciwnym razie dotychczasowe zachowanie).

**Sieci nigdy nie banowane.** Zbanować można tylko ruch zewnętrzny: host lokalny, Tailscale (`100.64.0.0/10`) i sieć lokalna — nigdy. Każdy wygenerowany jail dostaje wiersz `ignoreip` z listą **dostarczoną przez sam omega-serv** (`omega-serv waf never-auto-block`, ustawienie `options.waf.reputation.never_auto_block`) — nigdy wpisaną na sztywno kopię. `ignoreip` zdefiniowany już w `[DEFAULT]` jest zachowywany i uzupełniany, nigdy nadpisywany. Mostek Tailscale nigdy nie przekazuje bana adresu wyłączonego: przy ustawieniach domyślnych nie przekazuje więc już niczego (Twoi zewnętrzni goście przychodzą ze swoim prawdziwym adresem publicznym). Z wyjątkiem pracy za lokalnym proxy: zobacz poprzedni akapit. Gdy omega-serv nie da się znaleźć lub jest zbyt stary, wyłączony jest tylko host lokalny, z ostrzeżeniem w raporcie. Istniejąca instalacja jest aktualizowana tylko z `--apply --force`.

## Katalog

**10 jaili**: 6 jaili podstawowych, instalowanych jeden raz, oraz 4 jaile RIPOSTE, instalowane dla **każdej** instancji omega-serv (z nazwą jej usługi jako przedrostkiem, np. `omega-serv-riposte-1h`).

| Jail | Źródło | Wyzwalacz |
|---|---|---|
| `omega-waf-blocklist-sync` | blocklista skryptu magnet omega-waf | każdy IP już zbanowany przez skrypt |
| `omega-waf-magnet-alerts` | alerty skryptu magnet omega-waf | 3 alerty / 5 min (ten sam próg co auto-ban skryptu) |
| `omega-serv-waf-block` | alerty natywnego WAF omega-serv | 3 rzeczywiste blokady / 10 min (nigdy przy `log-only`) |
| `omega-serv-active-defense` | wzbogacony dziennik Active Defense | 2 żądania `hostile`/`contained` / 15 min |
| `omega-serv-auth-bruteforce` | log dostępu omega-serv | 5 odpowiedzi `401` / 5 min |
| `omega-serv-scan` | log dostępu omega-serv | 15 odpowiedzi `404` / 2 min |
| `<service>-riposte-1h` | bany sieciowe RIPOSTE (omega-serv 2.1.0), jeden zestaw na instancję | progi od 1 h do mniej niż 6 h: ban na 1 h |
| `<service>-riposte-6h` | bany sieciowe RIPOSTE (omega-serv 2.1.0), jeden zestaw na instancję | progi od 6 h do mniej niż 24 h: ban na 6 h |
| `<service>-riposte-24h` | bany sieciowe RIPOSTE (omega-serv 2.1.0), jeden zestaw na instancję | progi od 24 h do mniej niż 7 dni: ban na 24 h |
| `<service>-riposte-7d` | bany sieciowe RIPOSTE (omega-serv 2.1.0), jeden zestaw na instancję | progi od 7 dni wzwyż: ban na 7 dni |

Każdy jail jest instalowany tylko wtedy, gdy odpowiednie źródło jest
naprawdę skonfigurowane w omega-serv (włączony natywny WAF, włączony
Active Defense, skonfigurowany dodatek `magnet`, włączony RIPOSTE z
banem sieciowym) — w przeciwnym razie jest zgłaszany jako nie mający
zastosowania, nigdy tworzony na ślepo.

**Jaile RIPOSTE (od 1.1.0).** RIPOSTE, moduł stopniowanej odpowiedzi
omega-serv 2.1.0, zapisuje każdy swój ban sieciowy w swoim dzienniku;
Omega-Jail instaluje cztery jaile o stałym czasie (1 h, 6 h, 24 h,
7 dni), a każdy stopień RIPOSTE trafia do najdłuższego, który go nie
przekracza. Wszystkie instancje omega-serv na maszynie są wykrywane
automatycznie (usługi systemd i rejestr instancji): każda dostaje
własne jaile, z nazwą swojej usługi jako przedrostkiem.

## Instalacja

```bash
[ -d omega-jail ] && echo "ℹ️ Już tu rozpakowano, krok pominięty." || tar -xzf omega-jail.tar.gz
cd omega-jail/
chmod +x install.sh
./install.sh
```

`install.sh` tworzy środowisko wirtualne, instaluje omega-jail
(`pip install -e .`, bez uprawnień roota na tym etapie), nadaje prawo
wykonywania `omega-jail.sh`/`install.sh` — po czym pyta o ścieżkę
instalacji omega-serv do ochrony: jeśli ją znasz, wpisanie jej wprost
jest najszybsze (bez wyszukiwania); puste pole uruchamia automatyczne
wyszukiwanie w `$HOME` (rozpoznawane po obecności `omega-serv.sh`,
kilka sekund) — jeden znaleziony kandydat jest zapisywany
automatycznie; brak lub kilka — pyta ponownie. Ścieżka jest
zapamiętywana w `.serv-root` (nigdy nie trafia do repozytorium): nie
trzeba jej już nigdy wpisywać.

**Aktualizacja.** Z folderu nadrzędnego rozpakuj archiwum na istniejący folder (`tar -xzf omega-jail.tar.gz`, bez zabezpieczenia „Już rozpakowano” powyżej), a następnie ponownie uruchom `./install.sh`: zapisana już ścieżka omega-serv zostaje zachowana. Jeśli katalog zawiera nowe stosowalne jaile (na przykład jaile RIPOSTE z wersji 1.1.0), są one wypisywane i instalowane po potwierdzeniu (`sudo`); już zainstalowane jaile nigdy nie są zmieniane. Omega-Fire pokazuje je potem automatycznie, bez dodatkowych ustawień.

## Użycie

Domyślnie przebieg próbny (dry-run) — nic nie jest zapisywane, dopóki
`--apply` nie zostanie wyraźnie podane. Żadnej ścieżki do wpisania:
omega-serv to ten zapisany przez `install.sh`, a jaile muszą zawsze
trafić do PRAWDZIWEGO katalogu fail2ban maszyny — `/etc/fail2ban/` jest
więc także wykrywany i sprawdzany automatycznie:

```bash
./omega-jail.sh
```

Rzeczywista instalacja (wymaga roota — zapis w `/etc/fail2ban/`,
przeładowanie `fail2ban-client`):

```bash
./omega-jail.sh --apply
```

Jeśli `/etc/fail2ban/` nie istnieje (fail2ban niezainstalowany),
polecenie kończy się czysto z jasnym komunikatem, zamiast przez pomyłkę
zapisać coś gdzie indziej.

Przydatne opcje:
- `--serv-root`: przyjmuje ścieżkę innego omega-serv do jednorazowego
  użycia, zamiast zapisanej przez `install.sh`.
- `--jail-d-dir`, `--filter-d-dir`, `--action-d-dir`: każda przyjmuje
  ścieżkę katalogu, potrzebną tylko, gdy fail2ban nie jest
  zainstalowany w standardowym miejscu.
- `--only`: przyjmuje nazwę jaila z katalogu, by zainstalować tylko ten
  jeden wpis (`--only riposte-7d`: 7-dniowy jail RIPOSTE każdej
  instancji).
- `--force`: nadpisuje istniejący plik `jail.d/` jaila z katalogu (bez
  tej opcji kolizja nazw plików jest zawsze zgłaszana i nigdy nie jest
  po cichu nadpisywana).
- `--tailscale-cidr`: przyjmuje zakres sieci w formacie CIDR traktowany
  jako Tailscale, jeśli inny niż `100.64.0.0/10`.
- `--serv-config`: przyjmuje ścieżkę, potrzebną tylko, gdy konfiguracja
  omega-serv nie leży w standardowym miejscu (`config/omega-serve.json`
  w używanej ścieżce omega-serv).

Każde uruchomienie można bezpiecznie powtórzyć: jail utworzony już przez
wcześniejsze uruchomienie (lub dowolny zewnętrzny jail, który już
monitoruje ten sam plik logu, pod dowolną nazwą) jest automatycznie
wykrywany i pomijany, nigdy dublowany.

## Kontakt i wsparcie

omega-jail nie ma interfejsu: funkcja **Kontakt i wsparcie** pozostałych narzędzi omega działa z wiersza poleceń.

```bash
./omega-jail.sh contact                              # kawa (PayPal), e-mail i formularz wsparcia
./omega-jail.sh declaration declare --pays FR        # pokazuje dokładną wiadomość, nic nie jest wysyłane
./omega-jail.sh declaration declare --pays FR --yes
./omega-jail.sh declaration status
./omega-jail.sh declaration withdraw --yes           # nie zgłaszaj mnie więcej
./omega-jail.sh version --check                      # najnowsza opublikowana wersja
```

Zgłoszenie jest dobrowolne, domyślnie wyłączone i wysyłane tylko raz: służy wyłącznie do liczenia użytkowników oraz, jeśli tego chcesz, ich kontynentu lub kraju (zamknięte listy, nigdy dowolny tekst). Wysyła losowo wygenerowany klucz, nazwę programu (`omega-jail`) i jego wersję; nigdy imienia i nazwiska, nazwy maszyny, ustawienia, celu ani wyniku. Adres IP nie jest zapisywany w zgłoszeniach, ale — jak przy każdej wizycie — przechodzi przez kontrole bezpieczeństwa i dziennik serwera odbiorczego. `version --check` odczytuje jedynie listę wersji opublikowanych na stronie; nic nie jest wysyłane.

## Wymagania

- Zainstalowany `fail2ban` (`fail2ban-client` musi być w `PATH`).
- Istniejąca, skonfigurowana instalacja omega-serv (natywny WAF, Active
  Defense i/lub dodatek `magnet` muszą być włączone w omega-serv, by
  odpowiednie jaile miały zastosowanie).

## Licencja

Rozpowszechniany na licencji MIT. Zobacz plik [LICENSE](../../../LICENSE).
