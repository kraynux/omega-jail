<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="512">
</div>

# 🔒 OMEGA-JAIL

**Paket jail Fail2ban yang kompatibel dengan Omega-serv, Omega-Fire, dan Omega-Waf**

> Dikembangkan oleh [kraynux](https://github.com/kraynux) untuk [Omega-Server](https://kraynux.snake-mackarel.ts.net)   

Halaman resmi: [OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**Bahasa:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

Katalog jail [fail2ban](https://www.fail2ban.org/) yang sudah dikonfigurasi
untuk `omega-serv` dan `omega-waf`.
Alih-alih membuat setiap jail secara manual di omega-fire, satu perintah
saja mendeteksi instalasi omega-serv Anda yang sebenarnya dan memasang
katalog yang lengkap dan konsisten, dengan menghormati semua yang sudah
ada.

Omega-Jail tidak menggantikan apa pun: omega-fire tetap satu-satunya alat
untuk memantau, mendaftar, dan membuka blokir sehari-hari; omega-serv dan
omega-waf tidak berubah. Omega-Jail hanya menaruh sekali, secara
idempoten, berkas standar fail2ban (`filter.d/`, `jail.d/`).

## Mengapa blokir di tingkat jaringan selain blokir di tingkat aplikasi?

omega-serv (WAF bawaan, Active Defense) dan omega-waf (skrip magnet)
sudah bisa memblokir permintaan di tingkat HTTP dan menjawab `451`.
Blokir di tingkat aplikasi ini masih memakan satu koneksi/satu thread.
Omega-Jail membawa keputusan yang sama ke tingkat jaringan (nftables,
lewat fail2ban): koneksi ditolak bahkan sebelum mencapai omega-serv, di
semua port — pelengkap pertahanan berlapis, bukan duplikasi.

**Pengecualian: Tailscale.** Di balik terowongan Tailscale, aturan
nftables yang menerima lalu lintas tepercaya selalu berjalan sebelum
aturan yang disisipkan fail2ban untuk memblokir — blokir jaringan tidak
berpengaruh bagi klien tersebut. Karena itu setiap jail dalam katalog
membawa sebuah jembatan: jika IP yang diblokir berada dalam rentang
Tailscale (`100.64.0.0/10` secara bawaan), blokir diteruskan ke
blocklist bawaan omega-serv, yang lalu menjawab `451` secara eksplisit —
perbedaan "diblokir/tidak diblokir" tetap terlihat bahkan lewat
Tailscale. Jembatan ini selalu *fail-open*: kesalahan di sini
(omega-serv tidak ada, konfigurasi tidak ditemukan) tidak pernah membuat
blokir jaringan biasa gagal bagi yang lain.

**Di balik proxy lokal (Tailscale Funnel, reverse proxy di mesin yang sama).** Koneksi lalu datang dari host lokal: blokir jaringan tidak pernah mengenai pengunjung. Omega-Jail mendeteksinya (proxy tepercaya omega-serv yang mencakup `127.0.0.1` atau `::1`) dan jembatan lalu meneruskan setiap blokir alamat publik ke blocklist omega-serv, yang menjawab `451` — jalur yang sama dengan skrip magnet. Jail RIPOSTE tidak diteruskan: RIPOSTE sudah memasang blokir lokalnya.

**Tempat jembatan berjalan.** `--apply` memasang salinan mandiri jembatan, milik root, di `/usr/local/lib/omega-jail/` (opsi `--bridge-dir`), dijalankan dengan Python sistem: fail2ban tidak lagi menjalankan kode yang berada di folder Omega-Jail, dan menghapus folder itu tidak lagi merusak jembatan. Setiap instans omega-serv punya aksi sendiri (`omega-jail-tailscale-bridge-<service>`), yang meneruskan ke blocklist **miliknya**. Jembatan menandai blokirnya dengan asal `omega-jail:<jail>` dan hanya mencabut miliknya sendiri, dalam satu operasi (omega-serv 2.6.1 atau lebih baru; jika tidak, perilaku sebelumnya).

**Jaringan yang tidak pernah diblokir.** Hanya lalu lintas eksternal yang bisa diblokir: host lokal, Tailscale (`100.64.0.0/10`), dan jaringan lokal tidak pernah. Setiap jail yang dibuat menerima baris `ignoreip` dengan daftar **yang diberikan oleh omega-serv sendiri** (`omega-serv waf never-auto-block`, pengaturan `options.waf.reputation.never_auto_block`) — tidak pernah salinan tetap di sini. `ignoreip` yang sudah ada di `[DEFAULT]` dipertahankan dan dilengkapi, tidak pernah ditimpa. Jembatan Tailscale tidak pernah meneruskan blokir untuk alamat yang dikecualikan: dengan pengaturan bawaan, jembatan ini tidak meneruskan apa pun lagi (pengunjung eksternal Anda datang dengan alamat publik aslinya). Kecuali di balik proxy lokal: lihat paragraf sebelumnya. Jika omega-serv tidak ditemukan atau terlalu lama, hanya host lokal yang dikecualikan, dengan peringatan di laporan. Instalasi yang sudah ada hanya diperbarui dengan `--apply --force`.

## Katalog

**10 jail**: 6 jail dasar, dipasang sekali, dan 4 jail RIPOSTE, dipasang untuk **setiap** instans omega-serv (diawali nama layanannya, mis. `omega-serv-riposte-1h`).

| Jail | Sumber | Pemicu |
|---|---|---|
| `omega-waf-blocklist-sync` | blocklist skrip magnet omega-waf | setiap IP yang sudah diblokir oleh skrip |
| `omega-waf-magnet-alerts` | peringatan skrip magnet omega-waf | 3 peringatan / 5 menit (ambang sama dengan blokir otomatis skrip) |
| `omega-serv-waf-block` | peringatan WAF bawaan omega-serv | 3 blokir nyata / 10 menit (tidak pernah pada `log-only`) |
| `omega-serv-active-defense` | log Active Defense yang diperkaya | 2 permintaan `hostile`/`contained` / 15 menit |
| `omega-serv-auth-bruteforce` | log akses omega-serv | 5 respons `401` / 5 menit |
| `omega-serv-scan` | log akses omega-serv | 15 respons `404` / 2 menit |
| `<service>-riposte-1h` | blokir jaringan RIPOSTE (omega-serv 2.1.0), satu set per instans | tingkat 1 jam hingga kurang dari 6 jam: ban 1 jam |
| `<service>-riposte-6h` | blokir jaringan RIPOSTE (omega-serv 2.1.0), satu set per instans | tingkat 6 jam hingga kurang dari 24 jam: ban 6 jam |
| `<service>-riposte-24h` | blokir jaringan RIPOSTE (omega-serv 2.1.0), satu set per instans | tingkat 24 jam hingga kurang dari 7 hari: ban 24 jam |
| `<service>-riposte-7d` | blokir jaringan RIPOSTE (omega-serv 2.1.0), satu set per instans | tingkat 7 hari atau lebih: ban 7 hari |

Setiap jail hanya dipasang jika sumbernya benar-benar dikonfigurasi di
omega-serv (WAF bawaan aktif, Active Defense aktif, ekstra `magnet`
dikonfigurasi, RIPOSTE aktif dengan blokir jaringan) — jika tidak, jail
dilaporkan tidak berlaku, tidak pernah dibuat secara membabi buta.

**Jail RIPOSTE (sejak 1.1.0).** RIPOSTE, modul respons bertingkat
omega-serv 2.1.0, menulis setiap blokir jaringannya ke jurnalnya;
Omega-Jail memasang empat jail dengan durasi tetap (1 jam, 6 jam,
24 jam, 7 hari) dan setiap tingkat RIPOSTE masuk ke jail terpanjang yang
tidak melampauinya. Semua instans omega-serv di mesin terdeteksi
otomatis (layanan systemd dan registri instans): masing-masing
mendapatkan jail sendiri, dengan nama layanannya sebagai awalan.

## Instalasi

```bash
[ -d omega-jail ] && echo "ℹ️ Sudah diekstrak di sini, langkah dilewati." || tar -xzf omega-jail.tar.gz
cd omega-jail/
chmod +x install.sh
./install.sh
```

`install.sh` membuat lingkungan virtual, memasang omega-jail
(`pip install -e .`, tanpa hak root untuk langkah ini), membuat
`omega-jail.sh`/`install.sh` dapat dijalankan — lalu menanyakan jalur
instalasi omega-serv yang akan dilindungi: jika Anda sudah tahu,
mengetiknya langsung adalah cara tercepat (tanpa pencarian); jika
dibiarkan kosong, pencarian otomatis di `$HOME` mengambil alih (dikenali
dari adanya `omega-serv.sh`, beberapa detik) — satu kandidat yang
ditemukan disimpan otomatis; nol atau beberapa, Anda ditanya lagi.
Jalur ini diingat di `.serv-root` (tidak pernah di-commit): Anda tidak
perlu mengetiknya lagi.

**Pembaruan.** Dari folder induk, ekstrak arsip menimpa folder yang ada (`tar -xzf omega-jail.tar.gz`, tanpa pemeriksaan “Sudah diekstrak” di atas), lalu jalankan lagi `./install.sh`: jalur omega-serv yang sudah tersimpan dipertahankan. Jika katalog berisi jail baru yang berlaku (misalnya jail RIPOSTE dari 1.1.0), jail tersebut dicantumkan lalu dipasang setelah konfirmasi (`sudo`); jail yang sudah terpasang tidak pernah disentuh. Omega-Fire kemudian menampilkannya secara otomatis, tanpa pengaturan lain.

## Penggunaan

Secara bawaan berupa uji coba (dry-run) — tidak menulis apa pun sampai
`--apply` diminta secara eksplisit. Tidak ada jalur yang perlu diketik:
omega-serv adalah yang disimpan oleh `install.sh`, dan jail harus selalu
masuk ke folder fail2ban YANG SEBENARNYA di mesin — `/etc/fail2ban/`
juga dideteksi dan diperiksa otomatis:

```bash
./omega-jail.sh
```

Pemasangan nyata (perlu root — menulis di `/etc/fail2ban/`, memuat
ulang `fail2ban-client`):

```bash
./omega-jail.sh --apply
```

Jika `/etc/fail2ban/` tidak ada (fail2ban belum terpasang), perintah
berhenti dengan rapi disertai pesan yang jelas, alih-alih menulis ke
tempat lain secara keliru.

Opsi yang berguna:
- `--serv-root`: menerima jalur omega-serv lain untuk dipakai sekali,
  menggantikan yang disimpan oleh `install.sh`.
- `--jail-d-dir`, `--filter-d-dir`, `--action-d-dir`: masing-masing
  menerima jalur folder, hanya perlu jika fail2ban tidak terpasang di
  lokasi standar.
- `--only`: menerima nama jail dari katalog, untuk memasang entri itu
  saja (`--only riposte-7d`: jail RIPOSTE 7 hari di setiap instans).
- `--force`: menimpa berkas `jail.d/` yang sudah ada untuk jail katalog
  (tanpa opsi ini, bentrok nama berkas selalu dilaporkan dan tidak
  pernah ditimpa diam-diam).
- `--tailscale-cidr`: menerima rentang jaringan berformat CIDR yang
  dianggap Tailscale, jika berbeda dari `100.64.0.0/10`.
- `--serv-config`: menerima sebuah jalur, hanya perlu jika konfigurasi
  omega-serv tidak berada di lokasi standar (`config/omega-serve.json`
  di bawah jalur omega-serv yang dipakai).

Setiap eksekusi aman diulang: jail yang sudah dibuat oleh eksekusi
sebelumnya (atau jail eksternal apa pun yang sudah memantau berkas log
yang sama, apa pun namanya) terdeteksi otomatis dan dilewati, tidak
pernah digandakan.

## Kontak dan dukungan

omega-jail tidak memiliki antarmuka: fungsi **Kontak dan dukungan** dari alat omega lainnya tersedia melalui baris perintah.

```bash
./omega-jail.sh contact                              # kopi (PayPal), email dan formulir dukungan
./omega-jail.sh declaration declare --pays FR        # menampilkan pesan persisnya, tidak ada yang dikirim
./omega-jail.sh declaration declare --pays FR --yes
./omega-jail.sh declaration status
./omega-jail.sh declaration withdraw --yes           # jangan daftarkan saya lagi
./omega-jail.sh version --check                      # versi terbaru yang dipublikasikan
```

Pendaftaran bersifat sukarela, nonaktif secara bawaan, dan dikirim hanya sekali: hanya digunakan untuk menghitung pengguna dan, jika Anda mau, benua atau negara mereka (daftar tertutup, tidak pernah teks bebas). Yang dikirim adalah kunci yang diambil secara acak, nama perangkat lunak (`omega-jail`), dan versinya; tidak pernah nama, nama mesin, pengaturan, target, maupun hasil. Alamat IP tidak disimpan dalam pendaftaran, tetapi, seperti setiap kunjungan, melewati pemeriksaan keamanan dan log server penerima. `version --check` hanya membaca daftar versi yang dipublikasikan di situs; tidak ada yang dikirim.

## Persyaratan

- `fail2ban` terpasang (`fail2ban-client` harus ada di `PATH`).
- Instalasi omega-serv yang sudah ada dan dikonfigurasi (WAF bawaan,
  Active Defense, dan/atau ekstra `magnet` harus aktif di omega-serv
  agar jail terkait dapat diterapkan).

## Lisensi

Didistribusikan dengan lisensi MIT. Lihat berkas [LICENSE](../../../LICENSE).
