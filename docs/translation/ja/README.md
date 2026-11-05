<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="384">
</div>

# 🔒 OMEGA-JAIL

**Omega-serv・Omega-Fire・Omega-Waf に対応した Fail2ban jail パック**

> 開発：[kraynux](https://github.com/kraynux)（[Omega-Server](https://kraynux.snake-mackarel.ts.net) 向け）   

公式ページ：[OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**言語：**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

`omega-serv` と `omega-waf` 向けにあらかじめ設定された
[fail2ban](https://www.fail2ban.org/) jail のカタログです。
omega-fire で jail を 1 つずつ手作業で作る代わりに、1 つのコマンドが実際の
omega-serv のインストールを検出し、既存のものをすべて尊重しながら、
完全で一貫したカタログをインストールします。

Omega-Jail は何も置き換えません。日々の監視・一覧表示・BAN 解除を行うのは
引き続き omega-fire だけで、omega-serv と omega-waf も変わりません。
Omega-Jail は fail2ban の標準ファイル（`filter.d/`、`jail.d/`）を一度だけ、
冪等に配置するだけです。

## アプリケーションでの BAN に加えて、なぜネットワークでの BAN なのか

omega-serv（ネイティブ WAF、Active Defense）と omega-waf（magnet スクリプト）は、
すでに HTTP レベルでリクエストをブロックし `451` を返せます。しかしこの
アプリケーションレベルのブロックでも、接続やスレッドを 1 つ消費します。
Omega-Jail は同じ判断をネットワークレベル（fail2ban 経由の nftables）に
持ち込みます。接続は omega-serv に届く前に、すべてのポートで拒否されます。
多層防御を補うものであり、重複ではありません。

**例外：Tailscale。** Tailscale トンネルの背後では、信頼できる通信を許可する
nftables のルールが、fail2ban が BAN のために挿入するルールより常に先に
適用されます。そのためこれらのクライアントにはネットワーク BAN が効きません。
そこでカタログの各 jail にはブリッジが組み込まれています。BAN された IP が
Tailscale の範囲（既定は `100.64.0.0/10`）に入る場合、BAN は omega-serv の
ネイティブ blocklist に引き継がれ、明示的に `451` を返します。Tailscale 経由でも
「BAN されている／いない」の違いが見えたままです。このブリッジは常に
*fail-open* です。ここでのエラー（omega-serv がない、設定が見つからない）が、
ほかの全員に対する通常のネットワーク BAN を失敗させることはありません。

**ローカルプロキシの背後（Tailscale Funnel、同じマシン上のリバースプロキシ）。** この場合、接続はローカルホストから届くため、ネットワーク BAN は訪問者に届きません。Omega-Jail はこれを検出し（`127.0.0.1` または `::1` を含む omega-serv の信頼できるプロキシ）、ブリッジは公開アドレスのすべての BAN を omega-serv の blocklist に引き継ぎ、そこが `451` を返します。magnet スクリプトと同じ経路です。RIPOSTE の jail は引き継ぎません。RIPOSTE がすでにローカル BAN を設定しているためです。

**決して BAN されないネットワーク。** BAN されうるのは外部の通信だけです。ローカルホスト、Tailscale（`100.64.0.0/10`）、ローカルネットワークは決して BAN されません。生成される各 jail には、**omega-serv 自身が提供する**リスト（`omega-serv waf never-auto-block`、設定 `options.waf.reputation.never_auto_block`）を含む `ignoreip` 行が付きます。ここに固定のコピーを書くことはありません。`[DEFAULT]` にすでに定義された `ignoreip` は残したうえで補完し、上書きしません。Tailscale ブリッジは除外対象アドレスの BAN を決して引き継ぎません。そのため既定の設定では、もう何も引き継ぎません（外部の訪問者は実際の公開アドレスで届きます）。ただし、ローカルプロキシの背後にある場合は前の段落を参照してください。omega-serv が見つからないか古すぎる場合は、ローカルホストだけを除外し、レポートに警告を出します。既存のインストールは `--apply --force` を指定したときだけ更新されます。

## カタログ

**全 10 jail**：基本の 6 jail は一度だけインストールされ、RIPOSTE の 4 jail は omega-serv の**各**インスタンスごとにインストールされます（サービス名が接頭辞になります。例：`omega-serv-riposte-1h`）。

| Jail | ソース | 発動条件 |
|---|---|---|
| `omega-waf-blocklist-sync` | omega-waf magnet スクリプトの blocklist | スクリプトがすでに BAN した IP すべて |
| `omega-waf-magnet-alerts` | omega-waf magnet スクリプトの警告 | 5 分間に 3 回の警告（スクリプトの自動 BAN と同じしきい値） |
| `omega-serv-waf-block` | omega-serv ネイティブ WAF の警告 | 10 分間に 3 回の実際のブロック（`log-only` では決して発動しない） |
| `omega-serv-active-defense` | Active Defense の拡張ログ | 15 分間に 2 件の `hostile`/`contained` リクエスト |
| `omega-serv-auth-bruteforce` | omega-serv のアクセスログ | 5 分間に 5 件の `401` 応答 |
| `omega-serv-scan` | omega-serv のアクセスログ | 2 分間に 15 件の `404` 応答 |
| `<service>-riposte-1h` | RIPOSTE のネットワーク BAN（omega-serv 2.1.0）、インスタンスごとに 1 組 | 1 時間以上 6 時間未満の段階：1 時間の BAN |
| `<service>-riposte-6h` | RIPOSTE のネットワーク BAN（omega-serv 2.1.0）、インスタンスごとに 1 組 | 6 時間以上 24 時間未満の段階：6 時間の BAN |
| `<service>-riposte-24h` | RIPOSTE のネットワーク BAN（omega-serv 2.1.0）、インスタンスごとに 1 組 | 24 時間以上 7 日未満の段階：24 時間の BAN |
| `<service>-riposte-7d` | RIPOSTE のネットワーク BAN（omega-serv 2.1.0）、インスタンスごとに 1 組 | 7 日以上の段階：7 日の BAN |

各 jail は、対応するソースが omega-serv 側で実際に設定されている場合
（ネイティブ WAF 有効、Active Defense 有効、`magnet` 拡張設定済み、
ネットワーク BAN つきで RIPOSTE 有効）にだけインストールされます。
そうでなければ適用外として報告され、やみくもに作られることはありません。

**RIPOSTE の jail（1.1.0 以降）。** omega-serv 2.1.0 の段階的対応モジュールである
RIPOSTE は、ネットワーク BAN を 1 件ずつ自身のジャーナルに書き込みます。
Omega-Jail は期間固定の 4 つの jail（1 時間、6 時間、24 時間、7 日）を
インストールし、RIPOSTE の各段階は、その段階を超えない最も長い jail に
割り当てられます。マシン上のすべての omega-serv インスタンスは自動的に
検出され（systemd サービスとインスタンスレジストリ）、それぞれがサービス名を
接頭辞とする専用の jail を持ちます。

## インストール

```bash
[ -d omega-jail ] && echo "ℹ️ ここに展開済みのため、手順をスキップします。" || tar -xzf omega-jail.tar.gz
cd omega-jail/
chmod +x install.sh
./install.sh
```

`install.sh` は仮想環境を作成し、omega-jail をインストールし
（`pip install -e .`、この手順に root 権限は不要）、
`omega-jail.sh`/`install.sh` を実行可能にします。続いて、保護する omega-serv の
インストール先パスを尋ねます。わかっていれば直接入力するのが最速です
（検索を省けます）。空欄のままにすると、`$HOME` 以下の自動検索が代わりに
行われます（`omega-serv.sh` の有無で判別、数秒）。候補が 1 つなら自動的に
保存され、0 個または複数なら再度尋ねます。このパスは `.serv-root` に
記録され（コミットされることはありません）、以後入力し直す必要はありません。

**更新。** 親フォルダーから、既存のフォルダーの上にアーカイブを展開し（`tar -xzf omega-jail.tar.gz`、上の「展開済み」チェックなし）、`./install.sh` を再実行します。保存済みの omega-serv のパスはそのまま使われます。カタログに適用可能な新しい jail（例：1.1.0 の RIPOSTE jail）があれば一覧表示され、確認後（`sudo`）にインストールされます。インストール済みの jail には一切触れません。その後、Omega-Fire が追加設定なしで自動的に表示します。

## 使い方

既定ではドライランです。`--apply` を明示的に指定するまで何も書き込みません。
パスを入力する必要はありません。omega-serv は `install.sh` が保存したものが
使われ、jail は常にマシンの本物の fail2ban ディレクトリに置かれる必要が
あるため、`/etc/fail2ban/` も自動的に検出・確認されます。

```bash
./omega-jail.sh
```

実際のインストール（root が必要：`/etc/fail2ban/` への書き込み、
`fail2ban-client` の再読み込み）：

```bash
./omega-jail.sh --apply
```

`/etc/fail2ban/` が存在しない場合（fail2ban 未インストール）、コマンドは
誤って別の場所に書き込むことなく、わかりやすいメッセージとともに
正しく終了します。

便利なオプション：
- `--serv-root`：`install.sh` が保存したものの代わりに、一時的に対象とする
  別の omega-serv のパスを指定します。
- `--jail-d-dir`、`--filter-d-dir`、`--action-d-dir`：それぞれディレクトリの
  パスを指定します。fail2ban が標準の場所にインストールされていない場合だけ
  必要です。
- `--only`：カタログの jail 名を指定し、その 1 項目だけをインストールします
  （`--only riposte-7d`：各インスタンスの 7 日間の RIPOSTE jail）。
- `--force`：カタログの jail について既存の `jail.d/` ファイルを上書きします
  （このオプションがなければ、ファイル名の衝突は常に報告され、黙って
  上書きされることはありません）。
- `--tailscale-cidr`：`100.64.0.0/10` と異なる場合に、Tailscale とみなす
  ネットワーク範囲を CIDR 形式で指定します。
- `--serv-config`：omega-serv の設定が標準の場所
  （使用する omega-serv のパス以下の `config/omega-serve.json`）にない場合だけ、
  そのパスを指定します。

何度実行しても安全です。以前の実行ですでに作られた jail（または、名前に
かかわらず同じログファイルをすでに監視している外部の jail）は自動的に
検出されてスキップされ、重複することはありません。

## 必要条件

- `fail2ban` がインストールされていること（`fail2ban-client` が `PATH` 上に
  あること）。
- 設定済みの既存 omega-serv インストール（対応する jail を適用可能にするには、
  omega-serv 側でネイティブ WAF、Active Defense、`magnet` 拡張のいずれか
  または複数が有効になっている必要があります）。

## ライセンス

MIT ライセンスで配布されています。[LICENSE](../../../LICENSE) ファイルを参照してください。
