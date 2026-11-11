<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="384">
</div>

# 🔒 OMEGA-JAIL

**Paquete de jails de Fail2ban compatible con Omega-serv, Omega-Fire y Omega-Waf**

> Desarrollado por [kraynux](https://github.com/kraynux) para [Omega-Server](https://kraynux.snake-mackarel.ts.net)   

Página oficial: [OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**Idiomas:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

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

**Detrás de un proxy local (Tailscale Funnel, proxy inverso en la misma máquina).** Las conexiones llegan entonces del host local: el baneo de red nunca alcanza al visitante. Omega-Jail lo detecta (proxy de confianza de omega-serv que cubre `127.0.0.1` o `::1`) y el puente retransmite entonces todo baneo de una dirección pública a la blocklist de omega-serv, que responde `451` — el mismo circuito que el script magnet. Los jails de RIPOSTE no se retransmiten: RIPOSTE ya aplicó su baneo local.

**Dónde se ejecuta el puente.** `--apply` instala una copia autónoma del puente, propiedad de root, en `/usr/local/lib/omega-jail/` (opción `--bridge-dir`), lanzada con el Python del sistema: fail2ban ya no ejecuta código situado en la carpeta de Omega-Jail, y borrar esa carpeta ya no rompe el puente. Cada instancia de omega-serv tiene su propia acción (`omega-jail-tailscale-bridge-<service>`), que reenvía a **su** blocklist. El puente marca sus bloqueos con el origen `omega-jail:<jail>` y solo levanta los suyos, en una sola operación (omega-serv 2.6.1 o posterior; si no, comportamiento anterior).

**Redes nunca baneadas.** Solo el tráfico externo puede ser baneado: el host local, Tailscale (`100.64.0.0/10`) y la red local nunca lo son. Cada jail generado recibe una línea `ignoreip` con la lista **proporcionada por el propio omega-serv** (`omega-serv waf never-auto-block`, ajuste `options.waf.reputation.never_auto_block`) — nunca una copia fija aquí. Un `ignoreip` ya definido en `[DEFAULT]` se conserva y se completa, nunca se sobrescribe. El puente Tailscale nunca retransmite el baneo de una dirección exenta: con los ajustes por defecto ya no retransmite nada (sus visitantes externos llegan con su dirección pública real). Salvo detrás de un proxy local: vea el párrafo anterior. Si omega-serv no se encuentra o es demasiado antiguo, solo el host local queda exento, con una advertencia en el informe. Una instalación existente solo se actualiza con `--apply --force`.

## Catálogo

**10 jails**: 6 jails base, instalados una sola vez, y 4 jails RIPOSTE, instalados para **cada** instancia de omega-serv (con el nombre de su servicio como prefijo, p. ej. `omega-serv-riposte-1h`).

| Jail | Fuente | Disparador |
|---|---|---|
| `omega-waf-blocklist-sync` | blocklist del script magnet de omega-waf | cualquier IP ya baneada por el script |
| `omega-waf-magnet-alerts` | alertas del script magnet de omega-waf | 3 alertas / 5 min (mismo umbral que el auto-ban del propio script) |
| `omega-serv-waf-block` | alertas del WAF nativo de omega-serv | 3 bloqueos reales / 10 min (nunca en `log-only`) |
| `omega-serv-active-defense` | registro enriquecido de Active Defense | 2 peticiones `hostile`/`contained` / 15 min |
| `omega-serv-auth-bruteforce` | log de acceso de omega-serv | 5 respuestas `401` / 5 min |
| `omega-serv-scan` | log de acceso de omega-serv | 15 respuestas `404` / 2 min |
| `<service>-riposte-1h` | bans de red de RIPOSTE (omega-serv 2.1.0), un juego por instancia | niveles de 1 h a menos de 6 h: ban de 1 h |
| `<service>-riposte-6h` | bans de red de RIPOSTE (omega-serv 2.1.0), un juego por instancia | niveles de 6 h a menos de 24 h: ban de 6 h |
| `<service>-riposte-24h` | bans de red de RIPOSTE (omega-serv 2.1.0), un juego por instancia | niveles de 24 h a menos de 7 días: ban de 24 h |
| `<service>-riposte-7d` | bans de red de RIPOSTE (omega-serv 2.1.0), un juego por instancia | niveles de 7 días o más: ban de 7 días |

Cada jail solo se instala si su fuente correspondiente está realmente
configurada en omega-serv (WAF nativo activado, Active Defense
activado, extra `magnet` configurado, RIPOSTE activado con el ban de
red) — en caso contrario se reporta como no aplicable, nunca se crea a
ciegas.

**Jails de RIPOSTE (desde la 1.1.0).** RIPOSTE, el módulo de respuesta
gradual de omega-serv 2.1.0, escribe cada uno de sus bans de red en su
diario; Omega-Jail instala cuatro jails de duración fija (1 h, 6 h,
24 h, 7 días) y cada nivel de RIPOSTE va a la más larga que no lo
supera. Todas las instancias de omega-serv de la máquina se detectan
automáticamente (servicios systemd y registro de instancias): cada una
recibe sus propias jails, con el nombre de su servicio como prefijo.

## Instalación

```bash
[ -d omega-jail ] && echo "ℹ️ Ya extraído aquí, paso omitido." || tar -xzf omega-jail.tar.gz
cd omega-jail/
chmod +x install.sh
./install.sh
```

`install.sh` crea el entorno virtual, instala omega-jail
(`pip install -e .`, no requiere privilegios root para este paso),
hace ejecutables `omega-jail.sh`/`install.sh` — y luego pregunta la
ruta de la instalación omega-serv a proteger: si ya la conoce,
escribirla directamente es lo más rápido (evita toda búsqueda); dejada
en blanco, una búsqueda automática bajo `$HOME` toma el relevo
(reconocida por la presencia de `omega-serv.sh`, unos segundos) — si
hay un único candidato, se guarda automáticamente; si hay cero o
varios, se lo vuelve a preguntar. Esa ruta se guarda en `.serv-root`
(nunca se commitea): después nunca hace falta volver a escribirla.

**Actualización.** Desde la carpeta superior, extraiga el archivo sobre la carpeta existente (`tar -xzf omega-jail.tar.gz`, sin la protección «Ya extraído» de arriba) y vuelva a ejecutar `./install.sh`: se conserva la ruta de omega-serv ya guardada. Si el catálogo contiene nuevos jails aplicables (por ejemplo los jails RIPOSTE de la 1.1.0), se listan y se instalan tras confirmación (`sudo`); los jails ya instalados nunca se tocan. Omega-Fire los muestra después automáticamente, sin más ajustes.

## Uso

Dry-run por defecto — nunca escribe nada hasta que se solicita
`--apply` explícitamente. No hay ninguna ruta que escribir: omega-serv
es la que guardó `install.sh`, y los jails siempre deben ir al
directorio REAL de fail2ban de la máquina — `/etc/fail2ban/` también
se detecta y verifica automáticamente:

```bash
./omega-jail.sh
```

Instalación real (requiere root — escritura bajo `/etc/fail2ban/`,
recarga de `fail2ban-client`):

```bash
./omega-jail.sh --apply
```

Si `/etc/fail2ban/` no existe (fail2ban no instalado), el comando
falla de forma limpia con un mensaje claro, en vez de escribir en un
lugar equivocado por error.

Opciones útiles:
- `--serv-root`: recibe la ruta de otro omega-serv al que apuntar
  puntualmente, en vez del guardado por `install.sh`.
- `--jail-d-dir`, `--filter-d-dir`, `--action-d-dir`: cada una recibe
  una ruta de directorio, solo necesaria si fail2ban no está instalado
  en la ubicación estándar.
- `--only`: recibe el nombre de un jail del catálogo, para instalar
  solo esa entrada (`--only riposte-7d`: la jail RIPOSTE de 7 días de
  cada instancia).
- `--force`: sobrescribe un archivo `jail.d/` ya presente para un jail
  del catálogo (sin esta opción, una colisión de nombre de archivo
  siempre se reporta y nunca se sobrescribe en silencio).
- `--tailscale-cidr`: recibe un rango de red en formato CIDR a
  considerar como Tailscale, si es distinto de `100.64.0.0/10`.
- `--serv-config`: recibe una ruta, solo necesaria si la configuración
  de omega-serv no está en la ubicación estándar
  (`config/omega-serve.json` bajo la ruta de omega-serv en uso).

Cada ejecución es segura de repetir: un jail ya creado por una
ejecución anterior (o cualquier jail externo que ya vigile el mismo
archivo de log, sea cual sea su nombre) se detecta automáticamente y
se omite, nunca se duplica.

## Contacto y soporte

omega-jail no tiene interfaz: la función **Contacto y soporte** de las demás herramientas omega pasa por la línea de comandos.

```bash
./omega-jail.sh contact                              # café (PayPal), correo y formulario del soporte
./omega-jail.sh declaration declare --pays FR        # muestra el mensaje exacto, no se envía nada
./omega-jail.sh declaration declare --pays FR --yes
./omega-jail.sh declaration status
./omega-jail.sh declaration withdraw --yes           # dejar de declararme
./omega-jail.sh version --check                      # última versión publicada
```

La declaración es voluntaria, está desactivada por defecto y se envía una sola vez: solo sirve para contar a los usuarios y, si se desea, su continente o su país (listas cerradas, nunca texto libre). Envía una clave elegida al azar, el nombre del programa (`omega-jail`) y su versión; nunca un nombre, un nombre de máquina, un ajuste, un objetivo ni un resultado. La dirección IP no se registra en las declaraciones, pero, como en cualquier visita, pasa por los controles de seguridad y el registro del servidor de recepción. `version --check` solo lee la lista de versiones publicadas en el sitio; no se envía nada.

## Requisitos

- `fail2ban` instalado (`fail2ban-client` debe estar en el `PATH`).
- Una instalación de omega-serv existente y configurada (el WAF
  nativo, Active Defense y/o el extra `magnet` deben estar activados
  en omega-serv para que los jails correspondientes se vuelvan
  aplicables).

## Licencia

Distribuido bajo licencia MIT. Ver el archivo [LICENSE](../../../LICENSE).
