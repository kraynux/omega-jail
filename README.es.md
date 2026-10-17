<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="384">
</div>

# 🔒 OMEGA-JAIL

**Paquete de jails de Fail2ban compatible con Omega-serv, Omega-Fire y Omega-Waf**

> Desarrollado por **kraynux** para **Omega-server** 
[kraynux.snake-mackarel](https://kraynux.snake-mackarel.ts.net)

Página oficial: [OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**Idiomas:**
[Français](README.md) · [English](README.en.md) · [Español](README.es.md) · [Русский](README.ru.md) · [中文](README.zh-CN.md)
---

Catálogo preconfigurado de jails de [fail2ban](https://www.fail2ban.org/)
para `omega-serv` y `omega-waf`.
En lugar de crear cada jail a mano en omega-fire, un único comando
detecta su instalación real de omega-serv e instala un catálogo
completo y coherente, respetando todo lo que ya existe.

Omega-Jail no sustituye nada: omega-fire sigue siendo la única
herramienta que vigila/lista/desbanea en el día a día; omega-serv y
omega-waf permanecen sin cambios. Omega-Jail solo deposita los
archivos estándar de fail2ban (`filter.d/`, `jail.d/`) una vez, de
forma idempotente.

## ¿Por qué un ban de red además de los bans aplicativos?

omega-serv (WAF nativo, Active Defense) y omega-waf (script magnet) ya
saben bloquear una petición a nivel HTTP y responder `451`. Ese
bloqueo aplicativo sigue costando una conexión/un hilo. Omega-Jail
traslada esas mismas decisiones al nivel de red (nftables, vía
fail2ban): la conexión se rechaza antes de llegar siquiera a
omega-serv, en todos los puertos — un complemento de defensa en
profundidad, nunca una duplicación.

**Excepción: Tailscale.** Detrás de un túnel Tailscale, la regla de
nftables que acepta el tráfico de confianza siempre pasa antes que la
que fail2ban inserta para banear — el ban de red se vuelve un no-op
para esos clientes. Por eso, cada jail del catálogo incluye un puente:
si la IP baneada cae dentro del rango de Tailscale (`100.64.0.0/10`
por defecto), el ban se traslada a la blocklist nativa de omega-serv,
que entonces responde un `451` explícito — la distinción
"baneado/no baneado" sigue siendo visible incluso vía Tailscale. Este
puente siempre es *fail-open*: un error aquí (omega-serv ausente,
configuración no encontrada) nunca hace fallar el ban de red por
defecto para los demás.

## Catálogo

| Jail | Fuente | Disparador |
|---|---|---|
| `omega-waf-blocklist-sync` | blocklist del script magnet de omega-waf | cualquier IP ya baneada por el script |
| `omega-waf-magnet-alerts` | alertas del script magnet de omega-waf | 3 alertas / 5 min (mismo umbral que el auto-ban del propio script) |
| `omega-serv-waf-block` | alertas del WAF nativo de omega-serv | 3 bloqueos reales / 10 min (nunca en `log-only`) |
| `omega-serv-active-defense` | registro enriquecido de Active Defense | 2 peticiones `hostile`/`contained` / 15 min |
| `omega-serv-auth-bruteforce` | log de acceso de omega-serv | 5 respuestas `401` / 5 min |
| `omega-serv-scan` | log de acceso de omega-serv | 15 respuestas `404` / 2 min |

Cada jail solo se instala si su fuente correspondiente está realmente
configurada en omega-serv (WAF nativo activado, Active Defense
activado, extra `magnet` configurado) — en caso contrario se reporta
como no aplicable, nunca se crea a ciegas.

## Instalación

```bash
cd omega-jail
./install.sh
```

Crea el entorno virtual e instala omega-jail (no requiere privilegios
root para este paso).

## Uso

Dry-run por defecto — nunca escribe nada hasta que se solicita
`--apply` explícitamente. `--serv-root` sigue siendo obligatorio (no
existe ninguna convención que permita adivinar dónde vive una
instalación omega-serv en un servidor real); en cambio, los jails
siempre deben ir al directorio REAL de fail2ban de la máquina —
`/etc/fail2ban/` se detecta y verifica automáticamente, sin necesidad
de indicarlo:

```bash
./omega-jail.sh --serv-root /ruta/a/omega-serv
```

Instalación real (requiere root — escritura bajo `/etc/fail2ban/`,
recarga de `fail2ban-client`):

```bash
./omega-jail.sh --serv-root /ruta/a/omega-serv --apply
```

Si `/etc/fail2ban/` no existe (fail2ban no instalado), el comando
falla de forma limpia con un mensaje claro, en vez de escribir en un
lugar equivocado por error.

Opciones útiles:
- `--jail-d-dir`/`--filter-d-dir`/`--action-d-dir <ruta>`: solo
  necesario si fail2ban no está instalado en la ubicación estándar.
- `--only <nombre-del-jail>`: instalar solo una entrada del catálogo.
- `--force`: sobrescribir un `jail.d/omega-jail-<nombre>.conf` ya
  presente (sin esta opción, una colisión de nombre de archivo siempre
  se reporta y nunca se sobrescribe en silencio).
- `--tailscale-cidr <cidr>`: rango a considerar como Tailscale, si es
  distinto de `100.64.0.0/10`.
- `--serv-config <ruta>`: solo necesario si la configuración de
  omega-serv no está en la ubicación estándar
  (`config/omega-serve.json` bajo `--serv-root`).

Cada ejecución es segura de repetir: un jail ya creado por una
ejecución anterior (o cualquier jail externo que ya vigile el mismo
archivo de log, sea cual sea su nombre) se detecta automáticamente y
se omite, nunca se duplica.

## Requisitos

- `fail2ban` instalado (`fail2ban-client` debe estar en el `PATH`).
- Una instalación de omega-serv existente y configurada (el WAF
  nativo, Active Defense y/o el extra `magnet` deben estar activados
  en omega-serv para que los jails correspondientes se vuelvan
  aplicables).

## Licencia

Distribuido bajo licencia MIT. Ver el archivo [LICENSE](LICENSE).
