<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="384">
</div>

# 🔒 OMEGA-JAIL

**兼容 Omega-serv、Omega-Fire 和 Omega-Waf 的 Fail2ban jail 预配置包**

> 由 **kraynux** 为 **Omega-server** 开发 
[kraynux.snake-mackarel](https://kraynux.snake-mackarel.ts.net)

官方页面：[OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**语言:**
[Français](README.md) · [English](README.en.md) · [Español](README.es.md) · [Русский](README.ru.md) · [中文](README.zh-CN.md)
---

为 `omega-serv` 和 `omega-waf`
预先配置的 [fail2ban](https://www.fail2ban.org/) jail 目录。无需在
omega-fire 中逐个手动创建 jail，一条命令即可检测您真实的 omega-serv
安装,并安装一套完整、一致的目录,同时尊重所有已存在的内容。

Omega-Jail 不替代任何组件:omega-fire 仍然是日常监控/列出/解封的唯一
工具;omega-serv 和 omega-waf 保持不变。Omega-Jail 只是一次性地、以
幂等方式放置标准的 fail2ban 文件(`filter.d/`、`jail.d/`)。

## 为什么要在应用层封禁之外再加网络层封禁?

omega-serv(原生 WAF、Active Defense)和 omega-waf(magnet 脚本)已经
能够在 HTTP 层阻止请求并返回 `451`。这种应用层阻止仍然会消耗一个
连接/一个线程。Omega-Jail 将同样的决策下沉到网络层(通过 fail2ban 操作
nftables):连接在到达 omega-serv 之前就被拒绝,且覆盖所有端口——这是
纵深防御的补充,绝非重复。

**例外情况:Tailscale。** 在 Tailscale 隧道之后,接受可信流量的
nftables 规则总是先于 fail2ban 插入的封禁规则执行——对这些客户端来说,
网络层封禁等于没有生效。因此,目录中的每个 jail 都内置了一个桥接机制:
如果被封禁的 IP 落在 Tailscale 地址段内(默认 `100.64.0.0/10`),封禁
将被转发给 omega-serv 的原生黑名单,后者随即明确返回 `451`——即使通过
Tailscale,"已封禁/未封禁"的区别依然可见。这个桥接机制始终采用
*fail-open*(失败即放行)策略:此处出现的任何错误(omega-serv 缺失、
找不到配置)都绝不会导致其他人的默认网络层封禁失效。

## 目录清单

| Jail | 来源 | 触发条件 |
|---|---|---|
| `omega-waf-blocklist-sync` | omega-waf magnet 脚本的黑名单 | 任何已被脚本封禁的 IP |
| `omega-waf-magnet-alerts` | omega-waf magnet 脚本的告警 | 5 分钟内 3 次告警(与脚本自身的自动封禁阈值一致) |
| `omega-serv-waf-block` | omega-serv 原生 WAF 告警 | 10 分钟内 3 次真实阻止(绝不针对 `log-only`) |
| `omega-serv-active-defense` | Active Defense 增强日志 | 15 分钟内 2 次 `hostile`/`contained` 请求 |
| `omega-serv-auth-bruteforce` | omega-serv 访问日志 | 5 分钟内 5 次 `401` 响应 |
| `omega-serv-scan` | omega-serv 访问日志 | 2 分钟内 15 次 `404` 响应 |

每个 jail 仅在 omega-serv 端真正配置了对应来源时才会安装(原生 WAF
已启用、Active Defense 已启用、`magnet` 扩展已配置)——否则会被标记为
不适用,绝不会盲目创建。

## 安装

```bash
[ -d omega-jail ] && echo "ℹ️ 已在此解压,跳过此步骤。" || tar -xzf omega-jail.tar.gz
cd omega-jail/
chmod +x install.sh
./install.sh
```

`install.sh` 会创建虚拟环境、安装 omega-jail(`pip install -e .`,此
步骤不需要 root 权限),并将 `omega-jail.sh`/`install.sh` 设为可执行。

## 使用方法

默认为 dry-run(演练模式)——在明确要求 `--apply` 之前绝不写入任何内容。
`--serv-root` 仍然是必填项(没有任何通用约定可以猜出真实服务器上
omega-serv 安装的位置);但 jail 必须始终写入机器上真正的 fail2ban
目录——`/etc/fail2ban/` 会被自动检测并校验,无需手动指定:

```bash
./omega-jail.sh --serv-root /path/to/omega-serv
```

实际安装(需要 root 权限——写入 `/etc/fail2ban/`,重新加载
`fail2ban-client`):

```bash
./omega-jail.sh --serv-root /path/to/omega-serv --apply
```

如果 `/etc/fail2ban/` 不存在(未安装 fail2ban),命令会明确失败并给出
清晰提示,而不会错误地写入别处。

常用选项:
- `--jail-d-dir`/`--filter-d-dir`/`--action-d-dir <路径>`:仅当
  fail2ban 未安装在标准位置时才需要。
- `--only <jail名称>`:仅安装目录中的单个条目。
- `--force`:覆盖已存在的 `jail.d/omega-jail-<名称>.conf`(不加此
  选项时,文件名冲突总会被报告,绝不会被静默覆盖)。
- `--tailscale-cidr <cidr>`:如果与默认值 `100.64.0.0/10` 不同,指定
  要视为 Tailscale 的地址段。
- `--serv-config <路径>`:仅当 omega-serv 的配置不在标准位置(即
  `--serv-root` 下的 `config/omega-serve.json`)时才需要指定。

每次执行都可以安全地重复运行:之前运行已创建的 jail(或任何已经监控
同一日志文件的外部 jail,无论其名称如何)都会被自动检测并跳过,绝不
会重复创建。

## 前置条件

- 已安装 `fail2ban`(`fail2ban-client` 必须在 `PATH` 中)。
- 一个已存在且已配置的 omega-serv 安装(必须在 omega-serv 端启用原生
  WAF、Active Defense 和/或 `magnet` 扩展,相应的 jail 才会变为适用)。

## 许可证

基于 MIT 许可证发布。详见 [LICENSE](LICENSE) 文件。
