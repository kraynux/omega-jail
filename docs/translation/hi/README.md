<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="384">
</div>

# 🔒 OMEGA-JAIL

**Omega-serv, Omega-Fire और Omega-Waf के साथ काम करने वाला Fail2ban jail पैक**

> [kraynux](https://github.com/kraynux) द्वारा [Omega-Server](https://kraynux.snake-mackarel.ts.net) के लिए विकसित   

आधिकारिक पेज: [OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**भाषाएँ:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

`omega-serv` और `omega-waf` के लिए पहले से कॉन्फ़िगर किए गए
[fail2ban](https://www.fail2ban.org/) jail की सूची।
omega-fire में हर jail को हाथ से बनाने के बजाय, एक ही कमांड आपकी असली
omega-serv इंस्टॉलेशन पहचानती है और जो कुछ पहले से है उसका पूरा सम्मान करते
हुए एक पूरी, सुसंगत सूची इंस्टॉल करती है।

Omega-Jail किसी चीज़ की जगह नहीं लेता: रोज़ की निगरानी, सूची देखना और प्रतिबंध
हटाना अब भी केवल omega-fire करता है; omega-serv और omega-waf वैसे ही रहते हैं।
Omega-Jail बस fail2ban की मानक फ़ाइलें (`filter.d/`, `jail.d/`) एक बार,
दोहराने पर भी सुरक्षित (idempotent) तरीके से रख देता है।

## एप्लिकेशन स्तर के प्रतिबंधों के अलावा नेटवर्क स्तर का प्रतिबंध क्यों?

omega-serv (अपना WAF, Active Defense) और omega-waf (magnet स्क्रिप्ट) पहले से
HTTP स्तर पर किसी अनुरोध को रोककर `451` जवाब दे सकते हैं। फिर भी एप्लिकेशन
स्तर की यह रोक एक कनेक्शन/एक थ्रेड खर्च करती है। Omega-Jail यही फ़ैसले नेटवर्क
स्तर (fail2ban के ज़रिए nftables) तक ले जाता है: कनेक्शन omega-serv तक पहुँचने
से पहले ही, सभी पोर्ट पर, ठुकरा दिया जाता है — यह परतदार सुरक्षा का पूरक है,
दोहराव नहीं।

**अपवाद: Tailscale।** Tailscale टनल के पीछे, भरोसेमंद ट्रैफ़िक को अनुमति देने
वाला nftables नियम हमेशा उस नियम से पहले चलता है जिसे fail2ban प्रतिबंध के लिए
जोड़ता है — इन क्लाइंट पर नेटवर्क प्रतिबंध का कोई असर नहीं होता। इसलिए सूची के
हर jail में एक पुल (bridge) होता है: अगर प्रतिबंधित IP Tailscale की रेंज
(डिफ़ॉल्ट `100.64.0.0/10`) में आता है, तो प्रतिबंध omega-serv की अपनी
blocklist तक पहुँचाया जाता है, जो तब साफ़ `451` लौटाती है — "प्रतिबंधित/
प्रतिबंधित नहीं" का फ़र्क Tailscale से भी दिखता रहता है। यह पुल हमेशा
*fail-open* रहता है: यहाँ की कोई गड़बड़ी (omega-serv नहीं मिला, कॉन्फ़िगरेशन
नहीं मिला) बाकी सबके लिए सामान्य नेटवर्क प्रतिबंध को कभी विफल नहीं करती।

**स्थानीय प्रॉक्सी के पीछे (Tailscale Funnel, उसी मशीन पर रिवर्स प्रॉक्सी)।** तब कनेक्शन स्थानीय होस्ट से आते हैं: नेटवर्क प्रतिबंध आगंतुक तक कभी नहीं पहुँचता। Omega-Jail इसे पहचानता है (omega-serv का विश्वसनीय प्रॉक्सी जो `127.0.0.1` या `::1` को शामिल करता है) और तब पुल किसी सार्वजनिक पते के हर प्रतिबंध को omega-serv की blocklist में भेजता है, जो `451` लौटाती है — magnet स्क्रिप्ट जैसा ही रास्ता। RIPOSTE jail आगे नहीं भेजे जाते: RIPOSTE अपना स्थानीय प्रतिबंध पहले ही लगा चुका है।

**कभी प्रतिबंधित न होने वाले नेटवर्क।** केवल बाहरी ट्रैफ़िक ही प्रतिबंधित हो सकता है: लोकल होस्ट, Tailscale (`100.64.0.0/10`) और लोकल नेटवर्क कभी नहीं। हर बनाए गए jail को एक `ignoreip` पंक्ति मिलती है, जिसमें **omega-serv द्वारा स्वयं दी गई** सूची होती है (`omega-serv waf never-auto-block`, सेटिंग `options.waf.reputation.never_auto_block`) — यहाँ कभी कोई स्थिर प्रति नहीं। `[DEFAULT]` में पहले से तय `ignoreip` रखा और पूरा किया जाता है, कभी ओवरराइट नहीं होता। Tailscale पुल किसी छूट प्राप्त पते का प्रतिबंध कभी आगे नहीं भेजता: डिफ़ॉल्ट सेटिंग में वह अब कुछ भी आगे नहीं भेजता (आपके बाहरी आगंतुक अपने असली सार्वजनिक पते से आते हैं)। स्थानीय प्रॉक्सी के पीछे होने पर अपवाद: पिछला अनुच्छेद देखें। omega-serv न मिले या बहुत पुराना हो, तो केवल लोकल होस्ट को छूट मिलती है, रिपोर्ट में चेतावनी के साथ। मौजूदा इंस्टॉलेशन केवल `--apply --force` से अपडेट होता है।

## सूची

**कुल 10 jail**: 6 मूल jail, जो एक बार स्थापित होते हैं, और 4 RIPOSTE jail, जो **हर** omega-serv इंस्टेंस के लिए स्थापित होते हैं (उसकी सेवा के नाम के उपसर्ग के साथ, जैसे `omega-serv-riposte-1h`)।

| Jail | स्रोत | ट्रिगर |
|---|---|---|
| `omega-waf-blocklist-sync` | omega-waf magnet स्क्रिप्ट की blocklist | स्क्रिप्ट द्वारा पहले से प्रतिबंधित हर IP |
| `omega-waf-magnet-alerts` | omega-waf magnet स्क्रिप्ट की चेतावनियाँ | 5 मिनट में 3 चेतावनियाँ (स्क्रिप्ट के स्वतः प्रतिबंध जैसी ही सीमा) |
| `omega-serv-waf-block` | omega-serv के अपने WAF की चेतावनियाँ | 10 मिनट में 3 असली रोक (`log-only` पर कभी नहीं) |
| `omega-serv-active-defense` | Active Defense का विस्तृत लॉग | 15 मिनट में 2 `hostile`/`contained` अनुरोध |
| `omega-serv-auth-bruteforce` | omega-serv का एक्सेस लॉग | 5 मिनट में 5 `401` जवाब |
| `omega-serv-scan` | omega-serv का एक्सेस लॉग | 2 मिनट में 15 `404` जवाब |
| `<service>-riposte-1h` | RIPOSTE के नेटवर्क प्रतिबंध (omega-serv 2.1.0), हर इंस्टेंस का एक सेट | 1 घंटे से 6 घंटे से कम तक के स्तर: 1 घंटे का प्रतिबंध |
| `<service>-riposte-6h` | RIPOSTE के नेटवर्क प्रतिबंध (omega-serv 2.1.0), हर इंस्टेंस का एक सेट | 6 घंटे से 24 घंटे से कम तक के स्तर: 6 घंटे का प्रतिबंध |
| `<service>-riposte-24h` | RIPOSTE के नेटवर्क प्रतिबंध (omega-serv 2.1.0), हर इंस्टेंस का एक सेट | 24 घंटे से 7 दिन से कम तक के स्तर: 24 घंटे का प्रतिबंध |
| `<service>-riposte-7d` | RIPOSTE के नेटवर्क प्रतिबंध (omega-serv 2.1.0), हर इंस्टेंस का एक सेट | 7 दिन या अधिक के स्तर: 7 दिन का प्रतिबंध |

हर jail तभी इंस्टॉल होता है जब उससे जुड़ा स्रोत omega-serv में सचमुच
कॉन्फ़िगर हो (अपना WAF चालू, Active Defense चालू, `magnet` एक्स्ट्रा कॉन्फ़िगर,
नेटवर्क प्रतिबंध के साथ RIPOSTE चालू) — वरना उसे लागू न होने वाला बताया जाता
है, बिना सोचे-समझे कभी नहीं बनाया जाता।

**RIPOSTE jail (1.1.0 से)।** RIPOSTE, omega-serv 2.1.0 का चरणबद्ध जवाबी
मॉड्यूल, अपना हर नेटवर्क प्रतिबंध अपने जर्नल में लिखता है; Omega-Jail तय अवधि
वाले चार jail (1 घंटा, 6 घंटे, 24 घंटे, 7 दिन) इंस्टॉल करता है, और RIPOSTE का
हर चरण उस सबसे लंबे jail में जाता है जो उस चरण से ज़्यादा न हो। मशीन के सभी
omega-serv इंस्टेंस अपने-आप पहचाने जाते हैं (systemd सेवाएँ और इंस्टेंस
रजिस्टर): हर एक को अपनी सेवा के नाम से शुरू होने वाले अपने jail मिलते हैं।

## इंस्टॉलेशन

```bash
[ -d omega-jail ] && echo "ℹ️ यहाँ पहले से निकाला जा चुका है, चरण छोड़ा गया।" || tar -xzf omega-jail.tar.gz
cd omega-jail/
chmod +x install.sh
./install.sh
```

`install.sh` वर्चुअल एनवायरनमेंट बनाता है, omega-jail इंस्टॉल करता है
(`pip install -e .`, इस चरण के लिए root अधिकार ज़रूरी नहीं), `omega-jail.sh`/
`install.sh` को चलाने योग्य बनाता है — फिर सुरक्षित की जाने वाली omega-serv
इंस्टॉलेशन का पाथ पूछता है: अगर आप उसे जानते हैं, तो सीधे लिखना सबसे तेज़ है
(कोई खोज नहीं); खाली छोड़ने पर `$HOME` के अंदर अपने-आप खोज होती है
(`omega-serv.sh` की मौजूदगी से पहचानी जाती है, कुछ सेकंड) — एक ही उम्मीदवार
मिले तो वह अपने-आप सहेजा जाता है; कोई नहीं या कई मिलें, तो वह फिर पूछता है। यह
पाथ `.serv-root` में याद रखा जाता है (कभी commit नहीं होता): उसके बाद आपको इसे
दोबारा लिखने की ज़रूरत नहीं पड़ती।

**अद्यतन।** मूल फ़ोल्डर से, आर्काइव को मौजूदा फ़ोल्डर के ऊपर निकालें (`tar -xzf omega-jail.tar.gz`, ऊपर की “पहले से निकाला गया” जाँच के बिना), फिर `./install.sh` दोबारा चलाएँ: पहले से सहेजा गया omega-serv पथ बना रहता है। यदि कैटलॉग में नए लागू होने योग्य jail हैं (जैसे 1.1.0 के RIPOSTE jail), तो उनकी सूची दिखाई जाती है और पुष्टि के बाद (`sudo`) वे स्थापित होते हैं; पहले से स्थापित jail को कभी नहीं छुआ जाता। इसके बाद Omega-Fire उन्हें बिना किसी अन्य सेटिंग के अपने आप दिखाता है।

## उपयोग

डिफ़ॉल्ट रूप से परीक्षण रन (dry-run) — जब तक `--apply` साफ़ तौर पर न माँगा जाए,
कुछ भी नहीं लिखा जाता। कोई पाथ लिखने की ज़रूरत नहीं: omega-serv वही है जिसे
`install.sh` ने सहेजा, और jail को हमेशा मशीन के असली fail2ban फ़ोल्डर में जाना
होता है — इसलिए `/etc/fail2ban/` भी अपने-आप पहचाना और जाँचा जाता है:

```bash
./omega-jail.sh
```

असली इंस्टॉलेशन (root ज़रूरी — `/etc/fail2ban/` में लिखना, `fail2ban-client`
दोबारा लोड करना):

```bash
./omega-jail.sh --apply
```

अगर `/etc/fail2ban/` मौजूद नहीं है (fail2ban इंस्टॉल नहीं), तो कमांड गलती से
कहीं और लिखने के बजाय साफ़ संदेश के साथ ठीक से रुक जाती है।

उपयोगी विकल्प:
- `--serv-root`: `install.sh` द्वारा सहेजे गए पाथ की जगह, एक बार के लिए किसी
  दूसरे omega-serv का पाथ लेता है।
- `--jail-d-dir`, `--filter-d-dir`, `--action-d-dir`: हर एक किसी फ़ोल्डर का पाथ
  लेता है, केवल तब ज़रूरी जब fail2ban मानक जगह पर इंस्टॉल न हो।
- `--only`: सूची के किसी jail का नाम लेता है, ताकि केवल वही प्रविष्टि इंस्टॉल हो
  (`--only riposte-7d`: हर इंस्टेंस का 7 दिन वाला RIPOSTE jail)।
- `--force`: सूची के किसी jail की पहले से मौजूद `jail.d/` फ़ाइल को ओवरराइट
  करता है (इस विकल्प के बिना फ़ाइल नाम का टकराव हमेशा बताया जाता है और चुपचाप
  ओवरराइट नहीं होता)।
- `--tailscale-cidr`: CIDR रूप में वह नेटवर्क रेंज लेता है जिसे Tailscale माना
  जाए, अगर वह `100.64.0.0/10` से अलग हो।
- `--serv-config`: एक पाथ लेता है, केवल तब ज़रूरी जब omega-serv का कॉन्फ़िगरेशन
  मानक जगह पर न हो (इस्तेमाल किए गए omega-serv पाथ के अंदर
  `config/omega-serve.json`)।

हर रन को दोहराना सुरक्षित है: पिछले रन में पहले से बना jail (या कोई भी बाहरी jail
जो किसी भी नाम से उसी लॉग फ़ाइल पर पहले से नज़र रखता है) अपने-आप पहचाना जाकर
छोड़ दिया जाता है, कभी दोहराया नहीं जाता।

## आवश्यकताएँ

- `fail2ban` इंस्टॉल हो (`fail2ban-client` `PATH` में होना चाहिए)।
- पहले से मौजूद और कॉन्फ़िगर omega-serv इंस्टॉलेशन (संबंधित jail लागू होने के
  लिए omega-serv में अपना WAF, Active Defense और/या `magnet` एक्स्ट्रा चालू होना
  चाहिए)।

## लाइसेंस

MIT लाइसेंस के तहत वितरित। [LICENSE](../../../LICENSE) फ़ाइल देखें।
