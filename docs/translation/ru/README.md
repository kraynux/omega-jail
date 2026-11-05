<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="384">
</div>

# 🔒 OMEGA-JAIL

**Набор jail'ов Fail2ban, совместимый с Omega-serv, Omega-Fire и Omega-Waf**

> Разработано [kraynux](https://github.com/kraynux) для [Omega-Server](https://kraynux.snake-mackarel.ts.net)   

Официальная страница: [OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**Языки:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

Готовый каталог jail'ов [fail2ban](https://www.fail2ban.org/) для
`omega-serv` и `omega-waf`.
Вместо того чтобы создавать каждый jail вручную в omega-fire, одна
команда определяет вашу реальную установку omega-serv и устанавливает
полный, согласованный каталог, не трогая всё, что уже существует.

Omega-Jail ничего не заменяет: omega-fire остаётся единственным
инструментом, который ежедневно следит/отображает список/снимает
баны; omega-serv и omega-waf остаются без изменений. Omega-Jail лишь
один раз создаёт стандартные файлы fail2ban (`filter.d/`, `jail.d/`),
идемпотентно.

## Зачем сетевой бан в дополнение к банам на уровне приложения?

omega-serv (встроенный WAF, Active Defense) и omega-waf (скрипт
magnet) уже умеют блокировать запрос на уровне HTTP и отвечать `451`.
Такая блокировка на уровне приложения всё равно расходует
соединение/поток. Omega-Jail переносит те же решения на уровень сети
(nftables, через fail2ban): соединение отклоняется ещё до того, как
оно достигнет omega-serv, на всех портах — это дополнение
многоуровневой защиты, а не дублирование.

**Исключение: Tailscale.** За туннелем Tailscale правило nftables,
разрешающее доверенный трафик, всегда выполняется раньше правила,
которое вставляет fail2ban для бана, — сетевой бан становится
бесполезным для таких клиентов. Поэтому каждый jail каталога содержит
мост: если заблокированный IP попадает в диапазон Tailscale
(`100.64.0.0/10` по умолчанию), бан передаётся в собственный blocklist
omega-serv, который затем отвечает явным `451` — различие
«заблокирован/не заблокирован» остаётся видимым даже через Tailscale.
Этот мост всегда *fail-open*: ошибка здесь (omega-serv отсутствует,
конфигурация не найдена) никогда не приводит к сбою стандартного
сетевого бана для всех остальных.

**За локальным прокси (Tailscale Funnel, обратный прокси на той же машине).** Соединения тогда приходят с локального хоста: сетевой бан никогда не затрагивает посетителя. Omega-Jail это обнаруживает (доверенный прокси omega-serv, охватывающий `127.0.0.1` или `::1`), и мост передаёт тогда каждый бан публичного адреса в blocklist omega-serv, который отвечает `451` — тот же путь, что и у скрипта magnet. Jail'ы RIPOSTE не передаются: RIPOSTE уже поставил свой локальный бан.

**Сети, которые никогда не банятся.** Забанить можно только внешний трафик: локальный хост, Tailscale (`100.64.0.0/10`) и локальная сеть не банятся никогда. Каждый сгенерированный jail получает строку `ignoreip` со списком, **предоставленным самим omega-serv** (`omega-serv waf never-auto-block`, параметр `options.waf.reputation.never_auto_block`), — никогда не жёстко прописанная копия. Уже заданный в `[DEFAULT]` `ignoreip` сохраняется и дополняется, но никогда не перезаписывается. Мост Tailscale никогда не передаёт бан исключённого адреса: при настройках по умолчанию он больше ничего не передаёт (внешние посетители приходят со своим реальным публичным адресом). Кроме работы за локальным прокси: см. предыдущий абзац. Если omega-serv не найден или слишком старый, исключается только локальный хост, с предупреждением в отчёте. Существующая установка обновляется только с `--apply --force`.

## Каталог

**10 jail'ов**: 6 базовых, устанавливаемых один раз, и 4 jail'а RIPOSTE, устанавливаемых для **каждого** экземпляра omega-serv (с именем его службы в качестве префикса, например `omega-serv-riposte-1h`).

| Jail | Источник | Условие срабатывания |
|---|---|---|
| `omega-waf-blocklist-sync` | blocklist скрипта magnet omega-waf | любой IP, уже заблокированный скриптом |
| `omega-waf-magnet-alerts` | оповещения скрипта magnet omega-waf | 3 оповещения / 5 мин (тот же порог, что и у собственного авто-бана скрипта) |
| `omega-serv-waf-block` | оповещения встроенного WAF omega-serv | 3 реальные блокировки / 10 мин (никогда при `log-only`) |
| `omega-serv-active-defense` | обогащённый журнал Active Defense | 2 запроса `hostile`/`contained` / 15 мин |
| `omega-serv-auth-bruteforce` | журнал доступа omega-serv | 5 ответов `401` / 5 мин |
| `omega-serv-scan` | журнал доступа omega-serv | 15 ответов `404` / 2 мин |
| `<service>-riposte-1h` | сетевые баны RIPOSTE (omega-serv 2.1.0), один набор на экземпляр | ступени от 1 ч до менее 6 ч: бан на 1 ч |
| `<service>-riposte-6h` | сетевые баны RIPOSTE (omega-serv 2.1.0), один набор на экземпляр | ступени от 6 ч до менее 24 ч: бан на 6 ч |
| `<service>-riposte-24h` | сетевые баны RIPOSTE (omega-serv 2.1.0), один набор на экземпляр | ступени от 24 ч до менее 7 дней: бан на 24 ч |
| `<service>-riposte-7d` | сетевые баны RIPOSTE (omega-serv 2.1.0), один набор на экземпляр | ступени от 7 дней и более: бан на 7 дней |

Каждый jail устанавливается только если соответствующий источник
действительно настроен на стороне omega-serv (встроенный WAF включён,
Active Defense включён, настроен дополнительный модуль `magnet`, RIPOSTE
включён с сетевыми банами) — иначе он отмечается как неприменимый и
никогда не создаётся наугад.

**Jails RIPOSTE (начиная с 1.1.0).** RIPOSTE, модуль ступенчатого ответа
omega-serv 2.1.0, записывает каждый свой сетевой бан в журнал;
Omega-Jail устанавливает четыре jail с фиксированным сроком (1 ч, 6 ч,
24 ч, 7 дней), и каждая ступень RIPOSTE попадает в самый длинный из
них, не превышающий её. Все экземпляры omega-serv на машине находятся
автоматически (службы systemd и реестр экземпляров): каждый получает
свои jail с именем своей службы в качестве префикса.

## Установка

```bash
[ -d omega-jail ] && echo "ℹ️ Уже распаковано здесь, шаг пропущен." || tar -xzf omega-jail.tar.gz
cd omega-jail/
chmod +x install.sh
./install.sh
```

`install.sh` создаёт виртуальное окружение, устанавливает omega-jail
(`pip install -e .`, для этого шага права root не требуются), делает
`omega-jail.sh`/`install.sh` исполняемыми — а затем спрашивает путь к
защищаемой установке omega-serv: если он уже известен, ввести его
напрямую — самый быстрый вариант (полностью пропускает поиск); оставив
поле пустым, включается автоматический поиск под `$HOME`
(определяется по наличию `omega-serv.sh`, несколько секунд) —
единственный найденный вариант сохраняется автоматически; ноль или
несколько — спрашивает снова. Этот путь запоминается в `.serv-root`
(никогда не коммитится): больше вводить его не нужно.

**Обновление.** Из родительской папки распакуйте архив поверх существующей папки (`tar -xzf omega-jail.tar.gz`, без проверки «Уже распаковано» выше), затем снова запустите `./install.sh`: уже сохранённый путь к omega-serv сохраняется. Если в каталоге есть новые применимые jail'ы (например, jail'ы RIPOSTE версии 1.1.0), они выводятся списком и устанавливаются после подтверждения (`sudo`); уже установленные jail'ы никогда не изменяются. Затем Omega-Fire показывает их автоматически, без дополнительных настроек.

## Использование

По умолчанию — пробный прогон (dry-run): ничего не записывается, пока
явно не указан `--apply`. Никакой путь вводить не нужно: omega-serv —
это тот, что сохранил `install.sh`, а jail'ы всегда должны попадать в
НАСТОЯЩИЙ каталог fail2ban на машине — `/etc/fail2ban/` тоже
определяется и проверяется автоматически:

```bash
./omega-jail.sh
```

Реальная установка (требует root — запись в `/etc/fail2ban/`,
перезагрузка `fail2ban-client`):

```bash
./omega-jail.sh --apply
```

Если `/etc/fail2ban/` не существует (fail2ban не установлен), команда
завершается чётким сообщением об ошибке, а не записью в неверное
место по ошибке.

Полезные параметры:
- `--serv-root`: принимает путь к другому omega-serv, чтобы разово
  указать его вместо того, что сохранил `install.sh`.
- `--jail-d-dir`, `--filter-d-dir`, `--action-d-dir`: каждый принимает
  путь к каталогу, нужны только если fail2ban установлен не в
  стандартном месте.
- `--only`: принимает имя jail'а из каталога, чтобы установить только
  эту запись (`--only riposte-7d`: 7-дневный jail RIPOSTE каждого
  экземпляра).
- `--force`: перезаписывает уже существующий файл `jail.d/` для jail'а
  из каталога (без этого параметра совпадение имени файла всегда
  сообщается и никогда не перезаписывается тихо).
- `--tailscale-cidr`: принимает диапазон сети в формате CIDR, который
  считается Tailscale, если отличается от `100.64.0.0/10`.
- `--serv-config`: принимает путь, нужен только если конфигурация
  omega-serv находится не в стандартном месте (`config/omega-serve.json`
  внутри используемого пути omega-serv).

Каждый запуск можно безопасно повторять: jail, уже созданный
предыдущим запуском (или любой внешний jail, уже следящий за тем же
файлом журнала, под любым именем), автоматически обнаруживается и
пропускается, никогда не дублируется.

## Требования

- Установлен `fail2ban` (`fail2ban-client` должен быть доступен в
  `PATH`).
- Существующая, настроенная установка omega-serv (встроенный WAF,
  Active Defense и/или дополнительный модуль `magnet` должны быть
  включены на стороне omega-serv, чтобы соответствующие jail'ы стали
  применимыми).

## Лицензия

Распространяется по лицензии MIT. См. файл [LICENSE](../../../LICENSE).
