<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="512">
</div>

# 🔒 OMEGA-JAIL

**Omega-serv, Omega-Fire, Omega-Waf와 호환되는 Fail2ban jail 팩**

> 개발: [kraynux](https://github.com/kraynux), [Omega-Server](https://kraynux.snake-mackarel.ts.net)용   

공식 페이지: [OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**언어:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

`omega-serv`와 `omega-waf`를 위해 미리 구성된
[fail2ban](https://www.fail2ban.org/) jail 카탈로그입니다.
omega-fire에서 jail을 하나씩 손으로 만드는 대신, 명령 하나가 실제 omega-serv
설치를 감지하고, 이미 있는 것을 모두 존중하면서 완전하고 일관된 카탈로그를
설치합니다.

Omega-Jail은 아무것도 대체하지 않습니다. 매일의 감시·목록 확인·차단 해제는
여전히 omega-fire만 담당하며, omega-serv와 omega-waf도 그대로입니다.
Omega-Jail은 fail2ban 표준 파일(`filter.d/`, `jail.d/`)을 한 번, 멱등적으로
배치할 뿐입니다.

## 애플리케이션 차단에 더해 왜 네트워크 차단인가?

omega-serv(기본 WAF, Active Defense)와 omega-waf(magnet 스크립트)는 이미 HTTP
수준에서 요청을 차단하고 `451`로 응답할 수 있습니다. 하지만 이 애플리케이션
수준의 차단도 연결 하나/스레드 하나를 소모합니다. Omega-Jail은 같은 결정을
네트워크 수준(fail2ban을 통한 nftables)으로 옮깁니다. 연결은 omega-serv에
닿기도 전에 모든 포트에서 거부됩니다. 다층 방어를 보완하는 것이지 중복이
아닙니다.

**예외: Tailscale.** Tailscale 터널 뒤에서는 신뢰된 트래픽을 허용하는
nftables 규칙이 fail2ban이 차단을 위해 넣는 규칙보다 항상 먼저 적용되므로,
이런 클라이언트에는 네트워크 차단이 효과가 없습니다. 그래서 카탈로그의 모든
jail에는 브리지가 들어 있습니다. 차단된 IP가 Tailscale 범위(기본값
`100.64.0.0/10`)에 속하면, 차단은 omega-serv의 기본 blocklist로 전달되고, 그러면
명시적으로 `451`을 응답합니다. Tailscale을 통해서도 "차단됨/차단 안 됨"의
구분이 그대로 보입니다. 이 브리지는 항상 *fail-open*입니다. 여기서의
오류(omega-serv 없음, 설정을 찾을 수 없음)가 다른 모든 사용자에 대한 일반
네트워크 차단을 실패하게 만드는 일은 없습니다.

**로컬 프록시 뒤(Tailscale Funnel, 같은 머신의 리버스 프록시).** 이때 연결은 로컬 호스트에서 오므로 네트워크 차단이 방문자에게 닿지 않습니다. Omega-Jail이 이를 감지하면(`127.0.0.1` 또는 `::1`을 포함하는 omega-serv의 신뢰 프록시) 브리지가 공인 주소의 모든 차단을 omega-serv의 blocklist로 전달하고, omega-serv가 `451`로 응답합니다. magnet 스크립트와 같은 경로입니다. RIPOSTE jail은 전달하지 않습니다. RIPOSTE가 이미 로컬 차단을 걸었기 때문입니다.

**브리지가 실행되는 곳.** `--apply`는 root 소유의 독립된 브리지 사본을 `/usr/local/lib/omega-jail/`(옵션 `--bridge-dir`)에 설치하고 시스템 Python으로 실행합니다. fail2ban은 더 이상 Omega-Jail 폴더에 있는 코드를 실행하지 않으며, 그 폴더를 지워도 브리지가 망가지지 않습니다. omega-serv 인스턴스마다 자체 액션(`omega-jail-tailscale-bridge-<service>`)이 있어 **자기** blocklist로 전달합니다. 브리지는 자신의 차단에 출처 `omega-jail:<jail>`를 표시하고 자신의 차단만 한 번의 작업으로 해제합니다(omega-serv 2.6.1 이상, 그 외에는 이전 동작).

**절대 차단되지 않는 네트워크.** 외부 트래픽만 차단될 수 있습니다. 로컬 호스트, Tailscale(`100.64.0.0/10`), 로컬 네트워크는 절대 차단되지 않습니다. 생성되는 각 jail에는 **omega-serv 자신이 제공하는** 목록(`omega-serv waf never-auto-block`, 설정 `options.waf.reputation.never_auto_block`)이 담긴 `ignoreip` 줄이 붙습니다. 여기에 고정된 사본을 두지 않습니다. `[DEFAULT]`에 이미 정의된 `ignoreip`는 유지하고 보완할 뿐 절대 덮어쓰지 않습니다. Tailscale 브리지는 예외 대상 주소의 차단을 절대 전달하지 않으므로, 기본 설정에서는 더 이상 아무것도 전달하지 않습니다(외부 방문자는 실제 공인 주소로 들어옵니다). 단, 로컬 프록시 뒤에 있는 경우는 앞 단락을 참고하세요. omega-serv를 찾을 수 없거나 너무 오래된 경우에는 로컬 호스트만 예외로 하고, 보고서에 경고를 남깁니다. 기존 설치는 `--apply --force`로만 갱신됩니다.

## 카탈로그

**총 10개 jail**: 기본 jail 6개는 한 번만 설치되고, RIPOSTE jail 4개는 omega-serv **인스턴스마다** 설치됩니다(서비스 이름이 접두사로 붙음, 예: `omega-serv-riposte-1h`).

| Jail | 출처 | 발동 조건 |
|---|---|---|
| `omega-waf-blocklist-sync` | omega-waf magnet 스크립트의 blocklist | 스크립트가 이미 차단한 모든 IP |
| `omega-waf-magnet-alerts` | omega-waf magnet 스크립트의 경고 | 5분에 경고 3회(스크립트의 자동 차단과 같은 기준) |
| `omega-serv-waf-block` | omega-serv 기본 WAF의 경고 | 10분에 실제 차단 3회(`log-only`에는 절대 반응하지 않음) |
| `omega-serv-active-defense` | Active Defense 확장 로그 | 15분에 `hostile`/`contained` 요청 2회 |
| `omega-serv-auth-bruteforce` | omega-serv 접근 로그 | 5분에 `401` 응답 5회 |
| `omega-serv-scan` | omega-serv 접근 로그 | 2분에 `404` 응답 15회 |
| `<service>-riposte-1h` | RIPOSTE 네트워크 차단(omega-serv 2.1.0), 인스턴스마다 한 세트 | 1시간 이상 6시간 미만 단계: 1시간 차단 |
| `<service>-riposte-6h` | RIPOSTE 네트워크 차단(omega-serv 2.1.0), 인스턴스마다 한 세트 | 6시간 이상 24시간 미만 단계: 6시간 차단 |
| `<service>-riposte-24h` | RIPOSTE 네트워크 차단(omega-serv 2.1.0), 인스턴스마다 한 세트 | 24시간 이상 7일 미만 단계: 24시간 차단 |
| `<service>-riposte-7d` | RIPOSTE 네트워크 차단(omega-serv 2.1.0), 인스턴스마다 한 세트 | 7일 이상 단계: 7일 차단 |

각 jail은 해당 출처가 omega-serv 쪽에 실제로 설정된 경우(기본 WAF 활성화,
Active Defense 활성화, `magnet` 확장 설정, 네트워크 차단을 포함한 RIPOSTE
활성화)에만 설치됩니다. 그렇지 않으면 적용 불가로 보고되며, 무작정 만들어지는
일은 없습니다.

**RIPOSTE jail(1.1.0부터).** omega-serv 2.1.0의 단계적 대응 모듈인 RIPOSTE는
네트워크 차단을 하나씩 자신의 저널에 기록합니다. Omega-Jail은 기간이 고정된
jail 네 개(1시간, 6시간, 24시간, 7일)를 설치하며, RIPOSTE의 각 단계는 그 단계를
넘지 않는 가장 긴 jail로 갑니다. 머신의 모든 omega-serv 인스턴스는 자동으로
감지되며(systemd 서비스와 인스턴스 레지스트리), 각 인스턴스는 자신의 서비스
이름을 접두사로 하는 전용 jail을 받습니다.

## 설치

```bash
[ -d omega-jail ] && echo "ℹ️ 이미 여기에 압축이 풀려 있어 단계를 건너뜁니다." || tar -xzf omega-jail.tar.gz
cd omega-jail/
chmod +x install.sh
./install.sh
```

`install.sh`는 가상 환경을 만들고 omega-jail을 설치하며(`pip install -e .`,
이 단계에는 root 권한이 필요 없음), `omega-jail.sh`/`install.sh`를 실행 가능하게
만든 뒤, 보호할 omega-serv 설치 경로를 묻습니다. 이미 알고 있다면 직접
입력하는 것이 가장 빠릅니다(검색 생략). 비워 두면 `$HOME` 아래 자동 검색이
대신 진행됩니다(`omega-serv.sh`의 존재로 인식, 몇 초). 후보가 하나면 자동으로
저장되고, 없거나 여럿이면 다시 묻습니다. 이 경로는 `.serv-root`에
기억되므로(커밋되지 않음) 이후 다시 입력할 필요가 없습니다.

**업데이트.** 상위 폴더에서 기존 폴더 위에 아카이브를 풀고(`tar -xzf omega-jail.tar.gz`, 위의 '이미 압축 해제됨' 확인 없이) `./install.sh`를 다시 실행하세요. 이미 저장된 omega-serv 경로는 그대로 유지됩니다. 카탈로그에 적용 가능한 새 jail(예: 1.1.0의 RIPOSTE jail)이 있으면 목록을 보여 준 뒤 확인을 거쳐(`sudo`) 설치합니다. 이미 설치된 jail은 절대 건드리지 않습니다. 그 후 Omega-Fire가 추가 설정 없이 자동으로 표시합니다.

## 사용법

기본값은 시험 실행(dry-run)이며, `--apply`를 명시적으로 지정하기 전에는 아무것도
쓰지 않습니다. 경로를 입력할 필요가 없습니다. omega-serv는 `install.sh`가 저장한
것을 사용하며, jail은 항상 머신의 실제 fail2ban 디렉터리에 들어가야 하므로
`/etc/fail2ban/`도 자동으로 감지·확인됩니다.

```bash
./omega-jail.sh
```

실제 설치(root 필요 — `/etc/fail2ban/`에 쓰기, `fail2ban-client` 다시 불러오기):

```bash
./omega-jail.sh --apply
```

`/etc/fail2ban/`이 없으면(fail2ban 미설치) 명령은 실수로 다른 곳에 쓰지 않고,
명확한 메시지와 함께 깔끔하게 종료됩니다.

유용한 옵션:
- `--serv-root`: `install.sh`가 저장한 것 대신, 한 번만 대상으로 할 다른
  omega-serv의 경로를 받습니다.
- `--jail-d-dir`, `--filter-d-dir`, `--action-d-dir`: 각각 디렉터리 경로를
  받습니다. fail2ban이 표준 위치에 설치되지 않은 경우에만 필요합니다.
- `--only`: 카탈로그의 jail 이름을 받아 그 항목 하나만 설치합니다
  (`--only riposte-7d`: 각 인스턴스의 7일 RIPOSTE jail).
- `--force`: 카탈로그 jail의 기존 `jail.d/` 파일을 덮어씁니다(이 옵션이 없으면
  파일 이름 충돌은 항상 보고되며 조용히 덮어쓰지 않습니다).
- `--tailscale-cidr`: `100.64.0.0/10`과 다를 경우 Tailscale로 취급할 네트워크
  범위를 CIDR 형식으로 받습니다.
- `--serv-config`: omega-serv 설정이 표준 위치(사용 중인 omega-serv 경로 아래
  `config/omega-serve.json`)에 없을 때만 그 경로를 받습니다.

몇 번을 실행해도 안전합니다. 이전 실행에서 이미 만든 jail(또는 이름과 관계없이
같은 로그 파일을 이미 감시하는 외부 jail)은 자동으로 감지되어 건너뛰며, 중복되지
않습니다.

## 문의 및 지원

omega-jail에는 화면이 없으므로, 다른 omega 도구의 **문의 및 지원** 기능은 명령줄로 사용합니다.

```bash
./omega-jail.sh contact                              # 커피(PayPal), 지원 이메일과 양식
./omega-jail.sh declaration declare --pays FR        # 보낼 메시지를 그대로 표시, 아무것도 보내지 않음
./omega-jail.sh declaration declare --pays FR --yes
./omega-jail.sh declaration status
./omega-jail.sh declaration withdraw --yes           # 등록 취소
./omega-jail.sh version --check                      # 최신 게시 버전
```

등록은 자발적이며 기본적으로 꺼져 있고 한 번만 전송됩니다. 사용자 수와, 원하면 사용자의 대륙 또는 국가(닫힌 목록, 자유 입력 없음)를 세는 데에만 쓰입니다. 무작위로 생성한 키, 소프트웨어 이름(`omega-jail`)과 버전만 보내며, 이름, 컴퓨터 이름, 설정, 대상, 결과는 절대 보내지 않습니다. IP 주소는 등록 정보에 저장되지 않지만, 모든 방문과 마찬가지로 수신 서버의 보안 검사와 로그를 거칩니다. `version --check`는 사이트에 게시된 버전 목록만 읽으며, 아무것도 보내지 않습니다.

## 요구 사항

- `fail2ban` 설치(`fail2ban-client`가 `PATH`에 있어야 함).
- 기존에 설정된 omega-serv 설치(해당 jail을 적용할 수 있으려면 omega-serv 쪽에서
  기본 WAF, Active Defense, `magnet` 확장 중 하나 이상이 활성화되어 있어야 함).

## 라이선스

MIT 라이선스로 배포됩니다. [LICENSE](../../../LICENSE) 파일을 참고하세요.
