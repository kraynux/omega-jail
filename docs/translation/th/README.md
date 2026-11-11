<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="384">
</div>

# 🔒 OMEGA-JAIL

**ชุด jail ของ Fail2ban ที่ใช้ได้กับ Omega-serv, Omega-Fire และ Omega-Waf**

> พัฒนาโดย [kraynux](https://github.com/kraynux) สำหรับ [Omega-Server](https://kraynux.snake-mackarel.ts.net)   

หน้าทางการ: [OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**ภาษา:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

แคตตาล็อก jail ของ [fail2ban](https://www.fail2ban.org/) ที่ตั้งค่าไว้ล่วงหน้า
สำหรับ `omega-serv` และ `omega-waf`
แทนที่จะสร้าง jail ทีละตัวด้วยมือใน omega-fire คำสั่งเดียวจะตรวจหาการติดตั้ง
omega-serv จริงของคุณ แล้วติดตั้งแคตตาล็อกที่ครบถ้วนและสอดคล้องกัน
โดยเคารพทุกอย่างที่มีอยู่แล้ว

Omega-Jail ไม่ได้มาแทนที่สิ่งใด omega-fire ยังเป็นเครื่องมือเดียวสำหรับเฝ้าดู
แสดงรายการ และปลดแบนในแต่ละวัน ส่วน omega-serv และ omega-waf ก็ไม่เปลี่ยนแปลง
Omega-Jail เพียงวางไฟล์มาตรฐานของ fail2ban (`filter.d/`, `jail.d/`) ครั้งเดียว
แบบทำซ้ำได้อย่างปลอดภัย (idempotent)

## ทำไมต้องแบนระดับเครือข่าย นอกเหนือจากการแบนระดับแอปพลิเคชัน?

omega-serv (WAF ในตัว, Active Defense) และ omega-waf (สคริปต์ magnet)
บล็อกคำขอในระดับ HTTP และตอบ `451` ได้อยู่แล้ว แต่การบล็อกระดับแอปพลิเคชันนี้
ยังใช้การเชื่อมต่อหนึ่งรายการ/เธรดหนึ่งเธรด Omega-Jail นำการตัดสินใจเดียวกันนี้
ไปไว้ที่ระดับเครือข่าย (nftables ผ่าน fail2ban) การเชื่อมต่อจะถูกปฏิเสธก่อนถึง
omega-serv ในทุกพอร์ต — เป็นส่วนเสริมของการป้องกันหลายชั้น ไม่ใช่การทำซ้ำ

**ข้อยกเว้น: Tailscale** หลังอุโมงค์ Tailscale กฎ nftables ที่ยอมรับทราฟฟิก
ที่เชื่อถือได้จะทำงานก่อนกฎที่ fail2ban แทรกเพื่อแบนเสมอ — การแบนระดับเครือข่าย
จึงไม่มีผลกับไคลเอนต์เหล่านี้ ดังนั้นทุก jail ในแคตตาล็อกจึงมีสะพานเชื่อมติดมาด้วย:
ถ้า IP ที่ถูกแบนอยู่ในช่วงของ Tailscale (ค่าเริ่มต้น `100.64.0.0/10`) การแบนจะถูก
ส่งต่อไปยัง blocklist ในตัวของ omega-serv ซึ่งจะตอบ `451` อย่างชัดเจน — ความต่าง
ระหว่าง "ถูกแบน/ไม่ถูกแบน" จึงยังมองเห็นได้แม้ผ่าน Tailscale สะพานนี้เป็นแบบ
*fail-open* เสมอ: ข้อผิดพลาดตรงนี้ (ไม่มี omega-serv, หาค่ากำหนดไม่พบ)
จะไม่ทำให้การแบนระดับเครือข่ายตามปกติของคนอื่นทั้งหมดล้มเหลว

**หลังพร็อกซีในเครื่อง (Tailscale Funnel, reverse proxy บนเครื่องเดียวกัน)** ในกรณีนี้การเชื่อมต่อมาจากเครื่องตัวเอง: การแบนเครือข่ายไม่เคยไปถึงผู้เยี่ยมชม Omega-Jail ตรวจพบกรณีนี้ (พร็อกซีที่เชื่อถือได้ของ omega-serv ครอบคลุม `127.0.0.1` หรือ `::1`) แล้วสะพานจะส่งต่อการแบนทุกครั้งของที่อยู่สาธารณะไปยัง blocklist ของ omega-serv ซึ่งตอบกลับ `451` — เส้นทางเดียวกับสคริปต์ magnet jail ของ RIPOSTE จะไม่ถูกส่งต่อ: RIPOSTE ได้แบนในเครื่องไว้แล้ว

**สะพานทำงานที่ใด** `--apply` จะติดตั้งสำเนาอิสระของสะพานซึ่งเป็นของ root ไว้ที่ `/usr/local/lib/omega-jail/` (ตัวเลือก `--bridge-dir`) และรันด้วย Python ของระบบ: fail2ban จะไม่รันโค้ดที่อยู่ในโฟลเดอร์ของ Omega-Jail อีกต่อไป และการลบโฟลเดอร์นั้นจะไม่ทำให้สะพานเสียอีก แต่ละอินสแตนซ์ของ omega-serv มีแอ็กชันของตนเอง (`omega-jail-tailscale-bridge-<service>`) ที่ส่งต่อไปยัง blocklist **ของตนเอง** สะพานจะทำเครื่องหมายการแบนด้วยแหล่งที่มา `omega-jail:<jail>` และยกเลิกเฉพาะการแบนของตนเองในการดำเนินการครั้งเดียว (omega-serv 2.6.1 ขึ้นไป มิฉะนั้นใช้พฤติกรรมเดิม)

**เครือข่ายที่ไม่ถูกแบนเลย** แบนได้เฉพาะทราฟฟิกจากภายนอก: เครื่องตัวเอง (localhost), Tailscale (`100.64.0.0/10`) และเครือข่ายภายในจะไม่ถูกแบนเลย ทุก jail ที่สร้างขึ้นจะได้บรรทัด `ignoreip` พร้อมรายการ**ที่ omega-serv เป็นผู้ให้มาเอง** (`omega-serv waf never-auto-block`, ค่ากำหนด `options.waf.reputation.never_auto_block`) — ไม่ใช่สำเนาที่เขียนตายตัวไว้ที่นี่ `ignoreip` ที่กำหนดไว้แล้วใน `[DEFAULT]` จะถูกเก็บไว้และเติมเพิ่ม ไม่ถูกเขียนทับ สะพาน Tailscale ไม่เคยส่งต่อการแบนของที่อยู่ที่ได้รับการยกเว้น: ด้วยค่าเริ่มต้น สะพานจึงไม่ส่งต่ออะไรอีกแล้ว (ผู้เยี่ยมชมภายนอกของคุณเข้ามาด้วยที่อยู่สาธารณะจริง) ยกเว้นเมื่ออยู่หลังพร็อกซีในเครื่อง: ดูย่อหน้าก่อนหน้า หากหา omega-serv ไม่พบหรือรุ่นเก่าเกินไป จะยกเว้นเฉพาะเครื่องตัวเอง พร้อมคำเตือนในรายงาน การติดตั้งที่มีอยู่จะถูกอัปเดตเฉพาะเมื่อใช้ `--apply --force`

## แคตตาล็อก

**10 jail**: jail พื้นฐาน 6 ตัว ติดตั้งครั้งเดียว และ jail RIPOSTE 4 ตัว ติดตั้งสำหรับ**แต่ละ**อินสแตนซ์ omega-serv (ขึ้นต้นด้วยชื่อบริการของอินสแตนซ์นั้น เช่น `omega-serv-riposte-1h`)

| Jail | แหล่งที่มา | เงื่อนไขที่ทำงาน |
|---|---|---|
| `omega-waf-blocklist-sync` | blocklist ของสคริปต์ magnet omega-waf | ทุก IP ที่สคริปต์แบนไปแล้ว |
| `omega-waf-magnet-alerts` | การแจ้งเตือนของสคริปต์ magnet omega-waf | 3 การแจ้งเตือน / 5 นาที (เกณฑ์เดียวกับการแบนอัตโนมัติของสคริปต์) |
| `omega-serv-waf-block` | การแจ้งเตือนของ WAF ในตัว omega-serv | บล็อกจริง 3 ครั้ง / 10 นาที (ไม่ทำงานกับ `log-only`) |
| `omega-serv-active-defense` | บันทึกแบบละเอียดของ Active Defense | 2 คำขอ `hostile`/`contained` / 15 นาที |
| `omega-serv-auth-bruteforce` | บันทึกการเข้าถึงของ omega-serv | 5 การตอบ `401` / 5 นาที |
| `omega-serv-scan` | บันทึกการเข้าถึงของ omega-serv | 15 การตอบ `404` / 2 นาที |
| `<service>-riposte-1h` | การแบนระดับเครือข่ายของ RIPOSTE (omega-serv 2.1.0) หนึ่งชุดต่ออินสแตนซ์ | ขั้นตั้งแต่ 1 ชม. ถึงไม่ถึง 6 ชม.: แบน 1 ชม. |
| `<service>-riposte-6h` | การแบนระดับเครือข่ายของ RIPOSTE (omega-serv 2.1.0) หนึ่งชุดต่ออินสแตนซ์ | ขั้นตั้งแต่ 6 ชม. ถึงไม่ถึง 24 ชม.: แบน 6 ชม. |
| `<service>-riposte-24h` | การแบนระดับเครือข่ายของ RIPOSTE (omega-serv 2.1.0) หนึ่งชุดต่ออินสแตนซ์ | ขั้นตั้งแต่ 24 ชม. ถึงไม่ถึง 7 วัน: แบน 24 ชม. |
| `<service>-riposte-7d` | การแบนระดับเครือข่ายของ RIPOSTE (omega-serv 2.1.0) หนึ่งชุดต่ออินสแตนซ์ | ขั้นตั้งแต่ 7 วันขึ้นไป: แบน 7 วัน |

แต่ละ jail จะถูกติดตั้งก็ต่อเมื่อแหล่งที่มาที่เกี่ยวข้องถูกตั้งค่าไว้จริงฝั่ง omega-serv
(เปิด WAF ในตัว, เปิด Active Defense, ตั้งค่าส่วนเสริม `magnet`, เปิด RIPOSTE
พร้อมการแบนระดับเครือข่าย) — มิฉะนั้นจะถูกรายงานว่าไม่เกี่ยวข้อง และไม่ถูกสร้าง
อย่างไม่ไตร่ตรอง

**Jail ของ RIPOSTE (ตั้งแต่ 1.1.0)** RIPOSTE โมดูลตอบโต้แบบเป็นขั้นของ
omega-serv 2.1.0 จะเขียนการแบนระดับเครือข่ายแต่ละครั้งลงในบันทึกของตน
Omega-Jail ติดตั้ง jail ระยะเวลาคงที่สี่ตัว (1 ชั่วโมง, 6 ชั่วโมง, 24 ชั่วโมง, 7 วัน)
และแต่ละขั้นของ RIPOSTE จะไปยัง jail ที่ยาวที่สุดซึ่งไม่เกินขั้นนั้น อินสแตนซ์
omega-serv ทั้งหมดบนเครื่องจะถูกตรวจพบโดยอัตโนมัติ (บริการ systemd และทะเบียน
อินสแตนซ์) แต่ละตัวจะได้ jail ของตนเอง โดยมีชื่อบริการเป็นคำนำหน้า

## การติดตั้ง

```bash
[ -d omega-jail ] && echo "ℹ️ แตกไฟล์ไว้ที่นี่แล้ว ข้ามขั้นตอนนี้" || tar -xzf omega-jail.tar.gz
cd omega-jail/
chmod +x install.sh
./install.sh
```

`install.sh` จะสร้างสภาพแวดล้อมเสมือน ติดตั้ง omega-jail
(`pip install -e .` ขั้นตอนนี้ไม่ต้องใช้สิทธิ์ root) ทำให้
`omega-jail.sh`/`install.sh` รันได้ — แล้วถามพาธของการติดตั้ง omega-serv
ที่ต้องการปกป้อง: ถ้าคุณรู้อยู่แล้ว การพิมพ์โดยตรงเร็วที่สุด (ไม่ต้องค้นหา)
ถ้าเว้นว่างไว้ การค้นหาอัตโนมัติใต้ `$HOME` จะทำงานแทน (รู้จำจากการมีไฟล์
`omega-serv.sh` ใช้เวลาไม่กี่วินาที) — ถ้าพบเพียงตัวเดียว จะบันทึกให้อัตโนมัติ
ถ้าไม่พบหรือพบหลายตัว จะถามคุณอีกครั้ง พาธนี้จะถูกจำไว้ใน `.serv-root`
(ไม่ถูก commit) คุณจึงไม่ต้องพิมพ์ซ้ำอีก

**การอัปเดต** จากโฟลเดอร์แม่ ให้แตกไฟล์เก็บถาวรทับโฟลเดอร์เดิม (`tar -xzf omega-jail.tar.gz` โดยไม่ใช้การตรวจ “แตกไฟล์แล้ว” ด้านบน) แล้วเรียก `./install.sh` อีกครั้ง: เส้นทาง omega-serv ที่บันทึกไว้จะคงเดิม หากแคตตาล็อกมี jail ใหม่ที่ใช้ได้ (เช่น jail RIPOSTE ของ 1.1.0) จะแสดงรายการแล้วติดตั้งหลังการยืนยัน (`sudo`) jail ที่ติดตั้งแล้วจะไม่ถูกแตะต้องเลย จากนั้น Omega-Fire จะแสดงโดยอัตโนมัติ ไม่ต้องตั้งค่าเพิ่ม

## การใช้งาน

ค่าเริ่มต้นคือทดลองรัน (dry-run) — จะไม่เขียนอะไรเลยจนกว่าจะสั่ง `--apply`
อย่างชัดเจน ไม่ต้องพิมพ์พาธ: omega-serv คือที่ `install.sh` บันทึกไว้ และ jail
ต้องไปอยู่ในโฟลเดอร์ fail2ban ตัวจริงของเครื่องเสมอ — `/etc/fail2ban/` จึงถูก
ตรวจหาและตรวจสอบโดยอัตโนมัติด้วย:

```bash
./omega-jail.sh
```

ติดตั้งจริง (ต้องใช้ root — เขียนไว้ใต้ `/etc/fail2ban/` และโหลด
`fail2ban-client` ใหม่):

```bash
./omega-jail.sh --apply
```

หากไม่มี `/etc/fail2ban/` (ยังไม่ได้ติดตั้ง fail2ban) คำสั่งจะหยุดอย่างเรียบร้อย
พร้อมข้อความที่ชัดเจน แทนที่จะเขียนผิดที่โดยไม่ตั้งใจ

ตัวเลือกที่มีประโยชน์:
- `--serv-root`: รับพาธของ omega-serv ตัวอื่นเพื่อใช้ชั่วคราว แทนที่ที่
  `install.sh` บันทึกไว้
- `--jail-d-dir`, `--filter-d-dir`, `--action-d-dir`: แต่ละตัวรับพาธของโฟลเดอร์
  จำเป็นเฉพาะเมื่อ fail2ban ไม่ได้ติดตั้งในตำแหน่งมาตรฐาน
- `--only`: รับชื่อ jail ในแคตตาล็อก เพื่อติดตั้งเฉพาะรายการนั้น
  (`--only riposte-7d`: jail ของ RIPOSTE 7 วันของทุกอินสแตนซ์)
- `--force`: เขียนทับไฟล์ `jail.d/` ที่มีอยู่แล้วของ jail ในแคตตาล็อก
  (หากไม่มีตัวเลือกนี้ ชื่อไฟล์ที่ชนกันจะถูกรายงานเสมอและไม่ถูกเขียนทับเงียบ ๆ)
- `--tailscale-cidr`: รับช่วงเครือข่ายในรูปแบบ CIDR ที่จะถือเป็น Tailscale
  หากต่างจาก `100.64.0.0/10`
- `--serv-config`: รับพาธ จำเป็นเฉพาะเมื่อค่ากำหนดของ omega-serv ไม่อยู่ใน
  ตำแหน่งมาตรฐาน (`config/omega-serve.json` ใต้พาธ omega-serv ที่ใช้)

รันซ้ำกี่ครั้งก็ปลอดภัย: jail ที่การรันครั้งก่อนสร้างไว้แล้ว (หรือ jail ภายนอกใด ๆ
ที่เฝ้าดูไฟล์บันทึกเดียวกันอยู่แล้ว ไม่ว่าชื่ออะไร) จะถูกตรวจพบและข้ามโดยอัตโนมัติ
ไม่ถูกสร้างซ้ำ

## ติดต่อและสนับสนุน

omega-jail ไม่มีหน้าจอโต้ตอบ: ฟังก์ชัน **ติดต่อและสนับสนุน** ของเครื่องมือ omega อื่น ๆ จึงใช้ผ่านบรรทัดคำสั่ง

```bash
./omega-jail.sh contact                              # กาแฟ (PayPal), อีเมลและแบบฟอร์มของฝ่ายสนับสนุน
./omega-jail.sh declaration declare --pays FR        # แสดงข้อความที่แน่นอน ไม่มีการส่งใด ๆ
./omega-jail.sh declaration declare --pays FR --yes
./omega-jail.sh declaration status
./omega-jail.sh declaration withdraw --yes           # ไม่ต้องลงทะเบียนฉันอีก
./omega-jail.sh version --check                      # เวอร์ชันล่าสุดที่เผยแพร่
```

การลงทะเบียนเป็นไปโดยสมัครใจ ปิดไว้เป็นค่าเริ่มต้น และส่งเพียงครั้งเดียว ใช้เพื่อนับจำนวนผู้ใช้เท่านั้น และหากต้องการ นับทวีปหรือประเทศของผู้ใช้ (รายการปิด ไม่มีข้อความอิสระ) ระบบจะส่งคีย์ที่สุ่มขึ้น ชื่อซอฟต์แวร์ (`omega-jail`) และเวอร์ชัน ไม่ส่งชื่อ ชื่อเครื่อง การตั้งค่า เป้าหมาย หรือผลลัพธ์ใด ๆ ที่อยู่ IP จะไม่ถูกบันทึกในการลงทะเบียน แต่เช่นเดียวกับการเข้าชมทุกครั้ง จะผ่านการตรวจสอบความปลอดภัยและบันทึกของเซิร์ฟเวอร์ที่รับข้อมูล `version --check` เพียงอ่านรายการเวอร์ชันที่เผยแพร่บนเว็บไซต์ ไม่มีการส่งข้อมูลใด ๆ

## ข้อกำหนดเบื้องต้น

- ติดตั้ง `fail2ban` แล้ว (`fail2ban-client` ต้องอยู่ใน `PATH`)
- มีการติดตั้ง omega-serv ที่ตั้งค่าไว้แล้ว (ต้องเปิด WAF ในตัว, Active Defense
  และ/หรือส่วนเสริม `magnet` ฝั่ง omega-serv เพื่อให้ jail ที่เกี่ยวข้องใช้ได้)

## สัญญาอนุญาต

เผยแพร่ภายใต้สัญญาอนุญาต MIT ดูไฟล์ [LICENSE](../../../LICENSE)
