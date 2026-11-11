<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="512">
</div>

# 🔒 OMEGA-JAIL

**Pacote de jails Fail2ban compatível com Omega-serv, Omega-Fire e Omega-Waf**

> Desenvolvido por [kraynux](https://github.com/kraynux) para [Omega-Server](https://kraynux.snake-mackarel.ts.net)   

Página oficial: [OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**Idiomas:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

Catálogo pré-configurado de jails do [fail2ban](https://www.fail2ban.org/)
para `omega-serv` e `omega-waf`.
Em vez de criar cada jail à mão no omega-fire, um único comando
detecta a sua instalação real do omega-serv e instala um catálogo
completo e coerente, respeitando tudo o que já existe.

O Omega-Jail não substitui nada: o omega-fire continua sendo a única
ferramenta que monitora, lista e desbane no dia a dia; o omega-serv e o
omega-waf permanecem inalterados. O Omega-Jail apenas deposita uma vez,
de forma idempotente, os arquivos padrão do fail2ban (`filter.d/`,
`jail.d/`).

## Por que um ban de rede além dos bans de aplicação?

O omega-serv (WAF nativo, Active Defense) e o omega-waf (script magnet)
já sabem bloquear uma requisição no nível HTTP e responder `451`. Esse
bloqueio na aplicação ainda custa uma conexão/uma thread. O Omega-Jail
leva essas mesmas decisões ao nível de rede (nftables, via fail2ban): a
conexão é recusada antes mesmo de chegar ao omega-serv, em todas as
portas — um complemento de defesa em profundidade, não uma duplicação.

**Exceção: Tailscale.** Atrás de um túnel Tailscale, a regra nftables
que aceita o tráfego confiável sempre vem antes da regra que o fail2ban
insere para banir — o ban de rede não tem efeito para esses clientes.
Cada jail do catálogo traz, portanto, uma ponte: se o IP banido estiver
na faixa do Tailscale (`100.64.0.0/10` por padrão), o ban é repassado à
blocklist nativa do omega-serv, que então responde um `451` explícito —
a distinção "banido/não banido" continua visível mesmo via Tailscale.
Essa ponte é sempre *fail-open*: um erro aqui (omega-serv ausente,
configuração não encontrada) nunca faz o ban de rede normal falhar para
todos os outros.

**Atrás de um proxy local (Tailscale Funnel, proxy reverso na mesma máquina).** As conexões chegam então do host local: o ban de rede nunca atinge o visitante. O Omega-Jail detecta isso (proxy confiável do omega-serv cobrindo `127.0.0.1` ou `::1`) e a ponte repassa então todo ban de um endereço público para a blocklist do omega-serv, que responde `451` — o mesmo circuito do script magnet. Os jails do RIPOSTE não são repassados: o RIPOSTE já aplicou seu ban local.

**Onde a ponte roda.** `--apply` instala uma cópia autônoma da ponte, pertencente ao root, em `/usr/local/lib/omega-jail/` (opção `--bridge-dir`), executada com o Python do sistema: o fail2ban não executa mais código situado na pasta do Omega-Jail, e apagar essa pasta não quebra mais a ponte. Cada instância do omega-serv tem sua própria ação (`omega-jail-tailscale-bridge-<service>`), que repassa para **a sua** blocklist. A ponte marca seus banimentos com a origem `omega-jail:<jail>` e só remove os seus, em uma única operação (omega-serv 2.6.1 ou mais recente; senão, comportamento anterior).

**Redes nunca banidas.** Só o tráfego externo pode ser banido: o host local, o Tailscale (`100.64.0.0/10`) e a rede local nunca são. Cada jail gerada recebe uma linha `ignoreip` com a lista **fornecida pelo próprio omega-serv** (`omega-serv waf never-auto-block`, configuração `options.waf.reputation.never_auto_block`) — nunca uma cópia fixa aqui. Um `ignoreip` já definido em `[DEFAULT]` é mantido e completado, nunca sobrescrito. A ponte Tailscale nunca repassa o ban de um endereço isento: com as configurações padrão, ela não repassa mais nada (seus visitantes externos chegam com o endereço público real). Exceto atrás de um proxy local: veja o parágrafo anterior. Se o omega-serv não for encontrado ou for antigo demais, só o host local fica isento, com um aviso no relatório. Uma instalação existente só é atualizada com `--apply --force`.

## Catálogo

**10 jails**: 6 jails básicos, instalados uma única vez, e 4 jails RIPOSTE, instalados para **cada** instância do omega-serv (com o nome do seu serviço como prefixo, ex. `omega-serv-riposte-1h`).

| Jail | Fonte | Gatilho |
|---|---|---|
| `omega-waf-blocklist-sync` | blocklist do script magnet omega-waf | qualquer IP já banido pelo script |
| `omega-waf-magnet-alerts` | alertas do script magnet omega-waf | 3 alertas / 5 min (mesmo limite do auto-ban do script) |
| `omega-serv-waf-block` | alertas do WAF nativo do omega-serv | 3 bloqueios reais / 10 min (nunca em `log-only`) |
| `omega-serv-active-defense` | registro enriquecido do Active Defense | 2 requisições `hostile`/`contained` / 15 min |
| `omega-serv-auth-bruteforce` | log de acesso do omega-serv | 5 respostas `401` / 5 min |
| `omega-serv-scan` | log de acesso do omega-serv | 15 respostas `404` / 2 min |
| `<service>-riposte-1h` | bans de rede do RIPOSTE (omega-serv 2.1.0), um conjunto por instância | níveis de 1 h a menos de 6 h: ban de 1 h |
| `<service>-riposte-6h` | bans de rede do RIPOSTE (omega-serv 2.1.0), um conjunto por instância | níveis de 6 h a menos de 24 h: ban de 6 h |
| `<service>-riposte-24h` | bans de rede do RIPOSTE (omega-serv 2.1.0), um conjunto por instância | níveis de 24 h a menos de 7 dias: ban de 24 h |
| `<service>-riposte-7d` | bans de rede do RIPOSTE (omega-serv 2.1.0), um conjunto por instância | níveis de 7 dias ou mais: ban de 7 dias |

Cada jail só é instalada se a fonte correspondente estiver realmente
configurada no omega-serv (WAF nativo ativado, Active Defense ativado,
extra `magnet` configurado, RIPOSTE ativado com o ban de rede) — caso
contrário, é indicada como não aplicável, nunca criada às cegas.

**Jails do RIPOSTE (desde a 1.1.0).** O RIPOSTE, módulo de resposta
gradual do omega-serv 2.1.0, grava cada um dos seus bans de rede no
próprio registro; o Omega-Jail instala quatro jails de duração fixa
(1 h, 6 h, 24 h, 7 dias) e cada nível do RIPOSTE vai para a mais longa
que não o ultrapassa. Todas as instâncias do omega-serv da máquina são
detectadas automaticamente (serviços systemd e registro de instâncias):
cada uma recebe suas próprias jails, com o nome do seu serviço como
prefixo.

## Instalação

```bash
[ -d omega-jail ] && echo "ℹ️ Já extraído aqui, etapa ignorada." || tar -xzf omega-jail.tar.gz
cd omega-jail/
chmod +x install.sh
./install.sh
```

O `install.sh` cria o ambiente virtual, instala o omega-jail
(`pip install -e .`, sem privilégios de root nesta etapa), torna
`omega-jail.sh`/`install.sh` executáveis — e depois pede o caminho da
instalação do omega-serv a proteger: se você já o conhece, digitá-lo
diretamente é o mais rápido (evita qualquer busca); deixado em branco,
uma busca automática em `$HOME` assume (reconhecida pela presença de
`omega-serv.sh`, alguns segundos) — um único candidato encontrado é
gravado automaticamente; nenhum ou vários, ele pergunta de novo. Esse
caminho fica guardado em `.serv-root` (nunca enviado ao repositório):
você nunca mais precisa digitá-lo.

**Atualização.** A partir da pasta superior, extraia o arquivo sobre a pasta existente (`tar -xzf omega-jail.tar.gz`, sem a proteção “Já extraído” acima) e execute novamente `./install.sh`: o caminho do omega-serv já registrado é mantido. Se o catálogo tiver novos jails aplicáveis (por exemplo os jails RIPOSTE da 1.1.0), eles são listados e instalados após confirmação (`sudo`); os jails já instalados nunca são alterados. O Omega-Fire os exibe depois automaticamente, sem outra configuração.

## Uso

Simulação (dry-run) por padrão — nunca grava nada enquanto `--apply`
não for pedido explicitamente. Nenhum caminho para digitar: o omega-serv
é o gravado pelo `install.sh`, e as jails devem sempre ir para a pasta
REAL do fail2ban da máquina — `/etc/fail2ban/` também é detectado e
verificado automaticamente:

```bash
./omega-jail.sh
```

Instalação real (exige root — grava em `/etc/fail2ban/`, recarrega o
`fail2ban-client`):

```bash
./omega-jail.sh --apply
```

Se `/etc/fail2ban/` não existir (fail2ban não instalado), o comando
falha de forma limpa com uma mensagem clara, em vez de gravar em outro
lugar por engano.

Opções úteis:
- `--serv-root`: recebe o caminho de outro omega-serv para usar
  pontualmente, no lugar do gravado pelo `install.sh`.
- `--jail-d-dir`, `--filter-d-dir`, `--action-d-dir`: recebem cada uma
  o caminho de uma pasta, só se o fail2ban não estiver instalado no
  local padrão.
- `--only`: recebe o nome de uma jail do catálogo, para instalar só
  essa entrada (`--only riposte-7d`: a jail RIPOSTE de 7 dias de cada
  instância).
- `--force`: sobrescreve um arquivo `jail.d/` já existente de uma jail
  do catálogo (sem esta opção, uma colisão de nome de arquivo é sempre
  indicada e nunca sobrescrita silenciosamente).
- `--tailscale-cidr`: recebe uma faixa de rede em formato CIDR a ser
  considerada Tailscale, se diferente de `100.64.0.0/10`.
- `--serv-config`: recebe um caminho, só se a configuração do omega-serv
  não estiver no local padrão (`config/omega-serve.json` dentro do
  caminho do omega-serv usado).

Cada execução pode ser repetida com segurança: uma jail já criada por
uma execução anterior (ou qualquer jail externa que já monitore o mesmo
arquivo de log, com qualquer nome) é detectada automaticamente e
ignorada, nunca duplicada.

## Contato e suporte

O omega-jail não tem interface: a função **Contato e suporte** das outras ferramentas omega passa pela linha de comando.

```bash
./omega-jail.sh contact                              # café (PayPal), e-mail e formulário do suporte
./omega-jail.sh declaration declare --pays FR        # mostra a mensagem exata, nada é enviado
./omega-jail.sh declaration declare --pays FR --yes
./omega-jail.sh declaration status
./omega-jail.sh declaration withdraw --yes           # não me declarar mais
./omega-jail.sh version --check                      # última versão publicada
```

A declaração é voluntária, desativada por padrão e enviada uma única vez: serve apenas para contar os usuários e, se desejado, seu continente ou país (listas fechadas, nunca texto livre). Ela envia uma chave sorteada ao acaso, o nome do software (`omega-jail`) e sua versão; nunca um nome, um nome de máquina, uma configuração, um alvo ou um resultado. O endereço IP não é registrado nas declarações, mas, como em qualquer visita, passa pelos controles de segurança e pelo registro do servidor de recepção. `version --check` apenas lê a lista de versões publicadas no site; nada é enviado.

## Requisitos

- `fail2ban` instalado (`fail2ban-client` deve estar no `PATH`).
- Uma instalação do omega-serv existente e configurada (WAF nativo,
  Active Defense e/ou o extra `magnet` devem estar ativados no
  omega-serv para que as jails correspondentes se tornem aplicáveis).

## Licença

Distribuído sob a licença MIT. Veja o arquivo [LICENSE](../../../LICENSE).
