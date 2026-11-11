<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="512">
</div>

# 🔒 OMEGA-JAIL

**حزمة jails لـ Fail2ban متوافقة مع Omega-serv وOmega-Fire وOmega-Waf**

> طوّرها [kraynux](https://github.com/kraynux) لـ [Omega-Server](https://kraynux.snake-mackarel.ts.net)   

الصفحة الرسمية: [OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**اللغات:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](../vi/README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](README.md)

---

فهرس مُعدّ مسبقًا من jails ‏[fail2ban](https://www.fail2ban.org/)
لـ `omega-serv` و`omega-waf`.
بدل إنشاء كل jail يدويًا في omega-fire، يكتشف أمر واحد تثبيت omega-serv
الحقيقي لديك ويثبّت فهرسًا كاملًا ومتّسقًا، مع احترام كل ما هو موجود مسبقًا.

لا يحلّ Omega-Jail محلّ أي شيء: يبقى omega-fire الأداة الوحيدة للمراقبة
والعرض ورفع الحظر يوميًا، ويبقى omega-serv وomega-waf دون تغيير. يكتفي
Omega-Jail بوضع ملفات fail2ban القياسية (`filter.d/`، `jail.d/`) مرة واحدة،
بطريقة آمنة عند التكرار.

## لماذا حظر على مستوى الشبكة إضافةً إلى الحظر على مستوى التطبيق؟

يعرف omega-serv (جدار الحماية WAF المدمج، Active Defense) وomega-waf (سكربت
magnet) أصلًا كيف يحجبان طلبًا على مستوى HTTP ويردّان بـ `451`. لكن هذا الحجب
على مستوى التطبيق ما زال يكلّف اتصالًا/خيطًا. ينقل Omega-Jail القرارات نفسها
إلى مستوى الشبكة (nftables عبر fail2ban): يُرفض الاتصال قبل أن يصل إلى
omega-serv أصلًا، على جميع المنافذ — وهو تكملة للدفاع متعدد الطبقات، لا تكرار.

**استثناء: Tailscale.** خلف نفق Tailscale، تُطبَّق دائمًا قاعدة nftables التي
تقبل الحركة الموثوقة قبل القاعدة التي يضيفها fail2ban للحظر — فلا يكون للحظر
الشبكي أي أثر على هؤلاء العملاء. لذلك يحمل كل jail في الفهرس جسرًا: إذا وقع
العنوان المحظور ضمن نطاق Tailscale (‏`100.64.0.0/10` افتراضيًا)، يُمرَّر الحظر
إلى قائمة الحظر المدمجة في omega-serv، التي تردّ عندئذ بـ `451` صريح — فيبقى
الفرق بين «محظور/غير محظور» ظاهرًا حتى عبر Tailscale. هذا الجسر دائمًا
*fail-open*: أي خطأ هنا (غياب omega-serv، عدم العثور على الإعداد) لا يُفشل
أبدًا الحظر الشبكي العادي لبقية المستخدمين.

**خلف وكيل محلي (Tailscale Funnel، وكيل عكسي على الجهاز نفسه).** تصل الاتصالات حينها من المضيف المحلي: لا يبلغ الحظر الشبكي الزائرَ أبدًا. يكتشف Omega-Jail ذلك (الوكيل الموثوق لـ omega-serv يشمل `127.0.0.1` أو `::1`) فيمرّر الجسر حينها كل حظر لعنوان عام إلى blocklist الخاصة بـ omega-serv، التي تجيب بـ `451` — المسار نفسه الذي يسلكه سكربت magnet. لا تُمرَّر jail ‏RIPOSTE: فقد وضع RIPOSTE حظره المحلي بالفعل.

**أين يعمل الجسر.** يثبّت `--apply` نسخة مستقلة من الجسر يملكها root في `/usr/local/lib/omega-jail/` (الخيار `--bridge-dir`)، وتُشغَّل بـ Python النظام: لم يعد fail2ban ينفّذ شيفرة موجودة في مجلد Omega-Jail، ولم يعد حذف هذا المجلد يعطّل الجسر. لكل نسخة من omega-serv إجراؤها الخاص (`omega-jail-tailscale-bridge-<service>`) الذي يمرّر إلى قائمة الحظر **الخاصة بها**. يَسِم الجسر حظره بالمصدر `omega-jail:<jail>` ولا يرفع إلا حظره هو، في عملية واحدة (omega-serv 2.6.1 أو أحدث؛ وإلا فالسلوك السابق).

**شبكات لا تُحظر أبدًا.** لا يمكن حظر إلا الحركة الخارجية: المضيف المحلي وTailscale (‏`100.64.0.0/10`) والشبكة المحلية لا تُحظر أبدًا. يتلقى كل jail مُنشأ سطر `ignoreip` بالقائمة **التي يقدّمها omega-serv نفسه** (`omega-serv waf never-auto-block`، الإعداد `options.waf.reputation.never_auto_block`) — وليس نسخة ثابتة مكتوبة هنا. يُحتفظ بأي `ignoreip` معرَّف مسبقًا في `[DEFAULT]` ويُستكمل، ولا يُستبدل أبدًا. لا يمرّر جسر Tailscale أبدًا حظر عنوان مستثنى: لذا مع الإعدادات الافتراضية لم يعد يمرّر شيئًا (يصل زوارك الخارجيون بعنوانهم العام الحقيقي). إلا خلف وكيل محلي: راجع الفقرة السابقة. إذا تعذّر العثور على omega-serv أو كان قديمًا جدًا، يُستثنى المضيف المحلي وحده، مع تحذير في التقرير. لا يُحدَّث تثبيت موجود إلا باستخدام `--apply --force`.

## الفهرس

**10 jail**: ستة jail أساسية تُثبَّت مرة واحدة، وأربعة jail لـ RIPOSTE تُثبَّت **لكل** نسخة من omega-serv (مسبوقة باسم خدمتها، مثل `omega-serv-riposte-1h`).

| Jail | المصدر | سبب التفعيل |
|---|---|---|
| `omega-waf-blocklist-sync` | قائمة حظر سكربت magnet في omega-waf | كل عنوان سبق أن حظره السكربت |
| `omega-waf-magnet-alerts` | تنبيهات سكربت magnet في omega-waf | 3 تنبيهات / 5 دقائق (العتبة نفسها للحظر التلقائي في السكربت) |
| `omega-serv-waf-block` | تنبيهات جدار الحماية المدمج في omega-serv | 3 عمليات حجب فعلية / 10 دقائق (لا يُفعَّل أبدًا مع `log-only`) |
| `omega-serv-active-defense` | السجل المُثرى لـ Active Defense | طلبان `hostile`/`contained` / 15 دقيقة |
| `omega-serv-auth-bruteforce` | سجل الوصول في omega-serv | 5 ردود `401` / 5 دقائق |
| `omega-serv-scan` | سجل الوصول في omega-serv | 15 ردًا `404` / دقيقتان |
| `<service>-riposte-1h` | الحظر الشبكي لـ RIPOSTE (‏omega-serv 2.1.0)، مجموعة لكل نسخة | درجات من ساعة إلى أقل من 6 ساعات: حظر ساعة |
| `<service>-riposte-6h` | الحظر الشبكي لـ RIPOSTE (‏omega-serv 2.1.0)، مجموعة لكل نسخة | درجات من 6 ساعات إلى أقل من 24 ساعة: حظر 6 ساعات |
| `<service>-riposte-24h` | الحظر الشبكي لـ RIPOSTE (‏omega-serv 2.1.0)، مجموعة لكل نسخة | درجات من 24 ساعة إلى أقل من 7 أيام: حظر 24 ساعة |
| `<service>-riposte-7d` | الحظر الشبكي لـ RIPOSTE (‏omega-serv 2.1.0)، مجموعة لكل نسخة | درجات من 7 أيام فأكثر: حظر 7 أيام |

لا يُثبَّت أي jail إلا إذا كان مصدره مُعدًّا فعلًا في omega-serv (جدار الحماية
المدمج مفعّل، Active Defense مفعّل، الإضافة `magnet` مُعدّة، RIPOSTE مفعّل مع
الحظر الشبكي) — وإلا يُبلَّغ عنه بأنه غير قابل للتطبيق، ولا يُنشأ أبدًا عشوائيًا.

**jails الخاصة بـ RIPOSTE (منذ 1.1.0).** يكتب RIPOSTE، وهو وحدة الرد المتدرّج
في omega-serv 2.1.0، كل حظر شبكي في سجلّه؛ ويثبّت Omega-Jail أربعة jails ثابتة
المدة (ساعة، 6 ساعات، 24 ساعة، 7 أيام)، وتذهب كل درجة من درجات RIPOSTE إلى
أطول jail لا تتجاوزها. تُكتشف كل نسخ omega-serv على الجهاز تلقائيًا (خدمات
systemd وسجلّ النسخ): وتحصل كل نسخة على jails خاصة بها، تبدأ باسم خدمتها.

## التثبيت

```bash
[ -d omega-jail ] && echo "ℹ️ مستخرج هنا مسبقًا، تم تخطي الخطوة." || tar -xzf omega-jail.tar.gz
cd omega-jail/
chmod +x install.sh
./install.sh
```

ينشئ `install.sh` البيئة الافتراضية، ويثبّت omega-jail (`pip install -e .`،
دون حاجة إلى صلاحيات root في هذه الخطوة)، ويجعل `omega-jail.sh`/`install.sh`
قابلين للتنفيذ — ثم يسأل عن مسار تثبيت omega-serv المراد حمايته: إن كنت تعرفه،
فكتابته مباشرة هي الأسرع (دون أي بحث)؛ وإن تركته فارغًا، يتولّى بحث تلقائي
داخل `$HOME` المهمة (يُتعرَّف عليه بوجود `omega-serv.sh`، بضع ثوانٍ) — إن وُجد
مرشّح واحد يُحفظ تلقائيًا؛ وإن لم يوجد أي مرشّح أو وُجد عدة، يسألك من جديد.
يُحفظ هذا المسار في `.serv-root` (لا يُرسل إلى المستودع أبدًا): فلا تحتاج إلى
كتابته مرة أخرى.

**التحديث.** من المجلد الأب، استخرج الأرشيف فوق المجلد الموجود (`tar -xzf omega-jail.tar.gz`، دون شرط «مستخرج مسبقًا» أعلاه)، ثم أعد تشغيل `./install.sh`: يُحتفظ بمسار omega-serv المحفوظ مسبقًا. إذا احتوى الفهرس على jail جديدة قابلة للتطبيق (مثل jail ‏RIPOSTE في الإصدار 1.1.0)، تُعرض قائمتها ثم تُثبَّت بعد التأكيد (`sudo`)؛ ولا تُمس الـ jail المثبتة مسبقًا أبدًا. بعد ذلك يعرضها Omega-Fire تلقائيًا دون أي إعداد آخر.

## الاستخدام

تشغيل تجريبي (dry-run) افتراضيًا — لا يُكتب أي شيء ما لم يُطلب `--apply`
صراحةً. لا مسار تحتاج إلى كتابته: omega-serv هو الذي حفظه `install.sh`، ويجب أن
تذهب jails دائمًا إلى مجلد fail2ban الحقيقي على الجهاز — لذا يُكتشف
`/etc/fail2ban/` ويُتحقق منه تلقائيًا أيضًا:

```bash
./omega-jail.sh
```

التثبيت الفعلي (يتطلب root — كتابة تحت `/etc/fail2ban/`، وإعادة تحميل
`fail2ban-client`):

```bash
./omega-jail.sh --apply
```

إذا لم يكن `/etc/fail2ban/` موجودًا (fail2ban غير مثبّت)، يتوقف الأمر بشكل سليم
مع رسالة واضحة، بدل الكتابة في مكان آخر عن طريق الخطأ.

خيارات مفيدة:
- `--serv-root`: يأخذ مسار omega-serv آخر لاستهدافه مرة واحدة، بدل المسار الذي
  حفظه `install.sh`.
- `--jail-d-dir`، `--filter-d-dir`، `--action-d-dir`: يأخذ كل منها مسار مجلد،
  ولا يلزم إلا إذا لم يكن fail2ban مثبّتًا في الموضع القياسي.
- `--only`: يأخذ اسم jail من الفهرس، لتثبيت هذا العنصر وحده
  (`--only riposte-7d`: jail RIPOSTE لمدة 7 أيام في كل نسخة).
- `--force`: يستبدل ملف `jail.d/` موجودًا لـ jail من الفهرس (من دون هذا الخيار،
  يُبلَّغ دائمًا عن تعارض أسماء الملفات ولا يُستبدل بصمت أبدًا).
- `--tailscale-cidr`: يأخذ نطاق شبكة بصيغة CIDR يُعدّ Tailscale، إن كان مختلفًا
  عن `100.64.0.0/10`.
- `--serv-config`: يأخذ مسارًا، ولا يلزم إلا إذا لم يكن إعداد omega-serv في
  الموضع القياسي (`config/omega-serve.json` تحت مسار omega-serv المستخدم).

كل تشغيل آمن عند إعادته: أي jail أنشأه تشغيل سابق (أو أي jail خارجي يراقب ملف
السجل نفسه مسبقًا، أيًّا كان اسمه) يُكتشف تلقائيًا ويُتخطّى، ولا يُكرَّر أبدًا.

## التواصل والدعم

لا يملك omega-jail واجهة: تتوفر ميزة **التواصل والدعم** الموجودة في أدوات omega الأخرى عبر سطر الأوامر.

```bash
./omega-jail.sh contact                              # القهوة (PayPal)، بريد الدعم ونموذجه
./omega-jail.sh declaration declare --pays FR        # يعرض الرسالة كما هي، لا يُرسل شيء
./omega-jail.sh declaration declare --pays FR --yes
./omega-jail.sh declaration status
./omega-jail.sh declaration withdraw --yes           # إلغاء تسجيلي
./omega-jail.sh version --check                      # أحدث إصدار منشور
```

التسجيل اختياري، ومعطّل افتراضيًا، ويُرسل مرة واحدة فقط: يُستخدم فقط لإحصاء المستخدمين، وإن رغبت، قارتهم أو بلدهم (قوائم مغلقة، دون أي نص حر). يُرسل مفتاحًا مولَّدًا عشوائيًا واسم البرنامج (`omega-jail`) وإصداره؛ ولا يُرسل أبدًا اسمًا أو اسم جهاز أو إعدادًا أو هدفًا أو نتيجة. لا يُحفظ عنوان IP في التسجيلات، لكنه، كأي زيارة، يمر عبر فحوص الأمان وسجل الخادم المستقبِل. يقرأ `version --check` قائمة الإصدارات المنشورة على الموقع فقط؛ ولا يُرسل شيء.

## المتطلبات

- تثبيت `fail2ban` (يجب أن يكون `fail2ban-client` ضمن `PATH`).
- تثبيت omega-serv موجود ومُعدّ (يجب تفعيل جدار الحماية المدمج وActive Defense
  و/أو الإضافة `magnet` في omega-serv لتصبح jails المقابلة قابلة للتطبيق).

## الترخيص

موزّع بموجب ترخيص MIT. راجع ملف [LICENSE](../../../LICENSE).
