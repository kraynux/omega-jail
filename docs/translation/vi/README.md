<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->
<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-jail.png" alt="Omega-jail" width="512">
</div>

# 🔒 OMEGA-JAIL

**Gói jail Fail2ban tương thích với Omega-serv, Omega-Fire và Omega-Waf**

> Phát triển bởi [kraynux](https://github.com/kraynux) cho [Omega-Server](https://kraynux.snake-mackarel.ts.net)   

Trang chính thức: [OMEGA-JAIL](https://kraynux.snake-mackarel.ts.net/omega-jail/)  
  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)

**Ngôn ngữ:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

Danh mục jail [fail2ban](https://www.fail2ban.org/) được cấu hình sẵn
cho `omega-serv` và `omega-waf`.
Thay vì tạo từng jail bằng tay trong omega-fire, một lệnh duy nhất phát
hiện bản cài đặt omega-serv thực tế của bạn và cài một danh mục đầy đủ,
nhất quán, tôn trọng mọi thứ đã có.

Omega-Jail không thay thế gì cả: omega-fire vẫn là công cụ duy nhất để
giám sát, liệt kê và gỡ cấm hằng ngày; omega-serv và omega-waf giữ
nguyên. Omega-Jail chỉ đặt một lần, theo cách lặp lại an toàn
(idempotent), các tệp chuẩn của fail2ban (`filter.d/`, `jail.d/`).

## Vì sao cần cấm ở tầng mạng ngoài các lệnh cấm ở tầng ứng dụng?

omega-serv (WAF gốc, Active Defense) và omega-waf (script magnet) đã
biết chặn một yêu cầu ở tầng HTTP và trả về `451`. Việc chặn ở tầng ứng
dụng này vẫn tốn một kết nối/một luồng. Omega-Jail đưa cùng các quyết
định đó xuống tầng mạng (nftables, qua fail2ban): kết nối bị từ chối
trước cả khi tới omega-serv, trên mọi cổng — một lớp bổ sung cho phòng
thủ nhiều tầng, không phải trùng lặp.

**Ngoại lệ: Tailscale.** Phía sau đường hầm Tailscale, quy tắc nftables
cho phép lưu lượng tin cậy luôn đứng trước quy tắc mà fail2ban chèn vào
để cấm — lệnh cấm ở tầng mạng không có tác dụng với các máy khách này.
Vì vậy mỗi jail trong danh mục đều kèm một cầu nối: nếu IP bị cấm nằm
trong dải Tailscale (mặc định `100.64.0.0/10`), lệnh cấm được chuyển sang
blocklist gốc của omega-serv, khi đó trả về `451` rõ ràng — sự phân biệt
"bị cấm/không bị cấm" vẫn thấy được cả qua Tailscale. Cầu nối này luôn
*fail-open*: một lỗi ở đây (thiếu omega-serv, không tìm thấy cấu hình)
không bao giờ làm hỏng lệnh cấm mạng thông thường cho mọi người khác.

**Phía sau một proxy cục bộ (Tailscale Funnel, reverse proxy trên cùng máy).** Khi đó các kết nối đến từ máy cục bộ: lệnh cấm mạng không bao giờ chạm tới khách truy cập. Omega-Jail phát hiện điều này (proxy tin cậy của omega-serv bao gồm `127.0.0.1` hoặc `::1`) và cầu nối khi đó chuyển mọi lệnh cấm địa chỉ công khai sang blocklist của omega-serv, vốn trả về `451` — cùng đường đi với script magnet. Các jail RIPOSTE không được chuyển: RIPOSTE đã đặt lệnh cấm cục bộ của mình.

**Cầu nối chạy ở đâu.** `--apply` cài một bản sao độc lập của cầu nối, thuộc sở hữu của root, vào `/usr/local/lib/omega-jail/` (tùy chọn `--bridge-dir`), chạy bằng Python của hệ thống: fail2ban không còn chạy mã nằm trong thư mục của Omega-Jail, và xóa thư mục đó không còn làm hỏng cầu nối. Mỗi phiên bản omega-serv có hành động riêng (`omega-jail-tailscale-bridge-<service>`), chuyển tiếp tới blocklist **của chính nó**. Cầu nối đánh dấu các lệnh cấm của mình bằng nguồn gốc `omega-jail:<jail>` và chỉ gỡ lệnh cấm của chính nó, trong một thao tác (omega-serv 2.6.1 trở lên; nếu không, giữ hành vi cũ).

**Các mạng không bao giờ bị cấm.** Chỉ lưu lượng bên ngoài mới có thể bị cấm: máy cục bộ, Tailscale (`100.64.0.0/10`) và mạng nội bộ thì không bao giờ. Mỗi jail được tạo nhận một dòng `ignoreip` với danh sách **do chính omega-serv cung cấp** (`omega-serv waf never-auto-block`, thiết lập `options.waf.reputation.never_auto_block`) — không bao giờ là bản chép cứng ở đây. Một `ignoreip` đã có trong `[DEFAULT]` được giữ lại và bổ sung, không bao giờ bị ghi đè. Cầu nối Tailscale không bao giờ chuyển lệnh cấm của một địa chỉ được miễn: với thiết lập mặc định, nó không còn chuyển gì nữa (khách bên ngoài của bạn đến bằng địa chỉ công khai thật). Trừ khi ở sau một proxy cục bộ: xem đoạn trước. Nếu không tìm thấy omega-serv hoặc phiên bản quá cũ, chỉ máy cục bộ được miễn, kèm cảnh báo trong báo cáo. Một bản cài đặt sẵn có chỉ được cập nhật với `--apply --force`.

## Danh mục

**10 jail**: 6 jail cơ bản, cài một lần, và 4 jail RIPOSTE, cài cho **mỗi** phiên bản omega-serv (có tiền tố là tên dịch vụ của nó, ví dụ `omega-serv-riposte-1h`).

| Jail | Nguồn | Điều kiện kích hoạt |
|---|---|---|
| `omega-waf-blocklist-sync` | blocklist của script magnet omega-waf | mọi IP đã bị script cấm |
| `omega-waf-magnet-alerts` | cảnh báo của script magnet omega-waf | 3 cảnh báo / 5 phút (cùng ngưỡng với tự cấm của script) |
| `omega-serv-waf-block` | cảnh báo của WAF gốc omega-serv | 3 lần chặn thật / 10 phút (không bao giờ với `log-only`) |
| `omega-serv-active-defense` | nhật ký làm giàu của Active Defense | 2 yêu cầu `hostile`/`contained` / 15 phút |
| `omega-serv-auth-bruteforce` | nhật ký truy cập omega-serv | 5 phản hồi `401` / 5 phút |
| `omega-serv-scan` | nhật ký truy cập omega-serv | 15 phản hồi `404` / 2 phút |
| `<service>-riposte-1h` | lệnh cấm mạng của RIPOSTE (omega-serv 2.1.0), một bộ cho mỗi phiên bản chạy | mức từ 1 giờ đến dưới 6 giờ: cấm 1 giờ |
| `<service>-riposte-6h` | lệnh cấm mạng của RIPOSTE (omega-serv 2.1.0), một bộ cho mỗi phiên bản chạy | mức từ 6 giờ đến dưới 24 giờ: cấm 6 giờ |
| `<service>-riposte-24h` | lệnh cấm mạng của RIPOSTE (omega-serv 2.1.0), một bộ cho mỗi phiên bản chạy | mức từ 24 giờ đến dưới 7 ngày: cấm 24 giờ |
| `<service>-riposte-7d` | lệnh cấm mạng của RIPOSTE (omega-serv 2.1.0), một bộ cho mỗi phiên bản chạy | mức từ 7 ngày trở lên: cấm 7 ngày |

Mỗi jail chỉ được cài nếu nguồn tương ứng thực sự được cấu hình ở phía
omega-serv (bật WAF gốc, bật Active Defense, cấu hình phần mở rộng
`magnet`, bật RIPOSTE với lệnh cấm mạng) — nếu không, nó được báo là
không áp dụng, không bao giờ tạo một cách mù quáng.

**Jail RIPOSTE (từ 1.1.0).** RIPOSTE, mô-đun phản ứng theo bậc của
omega-serv 2.1.0, ghi mỗi lệnh cấm mạng vào nhật ký của mình; Omega-Jail
cài bốn jail có thời hạn cố định (1 giờ, 6 giờ, 24 giờ, 7 ngày) và mỗi
bậc của RIPOSTE đi tới jail dài nhất không vượt quá nó. Mọi phiên bản
omega-serv trên máy đều được phát hiện tự động (dịch vụ systemd và sổ
đăng ký phiên bản): mỗi phiên bản có jail riêng, với tên dịch vụ của nó
làm tiền tố.

## Cài đặt

```bash
[ -d omega-jail ] && echo "ℹ️ Đã giải nén ở đây, bỏ qua bước này." || tar -xzf omega-jail.tar.gz
cd omega-jail/
chmod +x install.sh
./install.sh
```

`install.sh` tạo môi trường ảo, cài omega-jail (`pip install -e .`,
không cần quyền root ở bước này), cấp quyền chạy cho
`omega-jail.sh`/`install.sh` — rồi hỏi đường dẫn của bản cài omega-serv
cần bảo vệ: nếu bạn đã biết, gõ trực tiếp là nhanh nhất (không phải tìm
kiếm); để trống, một cuộc tìm kiếm tự động trong `$HOME` sẽ thay thế
(nhận ra nhờ có `omega-serv.sh`, vài giây) — nếu tìm thấy đúng một ứng
viên, nó được lưu tự động; không có hoặc có nhiều, nó sẽ hỏi lại. Đường
dẫn được ghi nhớ trong `.serv-root` (không bao giờ commit): sau đó bạn
không bao giờ phải gõ lại.

**Cập nhật.** Từ thư mục cha, giải nén tệp lưu trữ đè lên thư mục hiện có (`tar -xzf omega-jail.tar.gz`, không dùng bước kiểm tra “Đã giải nén” ở trên), rồi chạy lại `./install.sh`: đường dẫn omega-serv đã lưu được giữ nguyên. Nếu danh mục có jail mới áp dụng được (ví dụ các jail RIPOSTE của bản 1.1.0), chúng được liệt kê rồi cài đặt sau khi xác nhận (`sudo`); các jail đã cài không bao giờ bị động đến. Sau đó Omega-Fire tự động hiển thị chúng, không cần cài đặt gì thêm.

## Sử dụng

Mặc định chạy thử (dry-run) — không ghi gì cho tới khi `--apply` được
yêu cầu rõ ràng. Không cần gõ đường dẫn: omega-serv là cái đã được
`install.sh` lưu, và các jail luôn phải vào thư mục fail2ban THẬT của
máy — vì vậy `/etc/fail2ban/` cũng được phát hiện và kiểm tra tự động:

```bash
./omega-jail.sh
```

Cài đặt thật (cần root — ghi vào `/etc/fail2ban/`, nạp lại
`fail2ban-client`):

```bash
./omega-jail.sh --apply
```

Nếu `/etc/fail2ban/` không tồn tại (chưa cài fail2ban), lệnh dừng gọn
gàng với một thông báo rõ ràng thay vì ghi nhầm sang chỗ khác.

Tùy chọn hữu ích:
- `--serv-root`: nhận đường dẫn của một omega-serv khác để dùng một
  lần, thay cho cái đã được `install.sh` lưu.
- `--jail-d-dir`, `--filter-d-dir`, `--action-d-dir`: mỗi tùy chọn nhận
  một đường dẫn thư mục, chỉ cần khi fail2ban không được cài ở vị trí
  chuẩn.
- `--only`: nhận tên một jail trong danh mục, để chỉ cài mục đó
  (`--only riposte-7d`: jail RIPOSTE 7 ngày của mỗi phiên bản).
- `--force`: ghi đè tệp `jail.d/` đã có của một jail trong danh mục
  (không có tùy chọn này, xung đột tên tệp luôn được báo và không bao
  giờ bị ghi đè âm thầm).
- `--tailscale-cidr`: nhận một dải mạng dạng CIDR được coi là
  Tailscale, nếu khác `100.64.0.0/10`.
- `--serv-config`: nhận một đường dẫn, chỉ cần khi cấu hình của
  omega-serv không nằm ở vị trí chuẩn (`config/omega-serve.json` dưới
  đường dẫn omega-serv đang dùng).

Mỗi lần chạy đều có thể lặp lại an toàn: một jail đã được lần chạy
trước tạo (hoặc bất kỳ jail bên ngoài nào đã theo dõi cùng tệp nhật ký,
dù tên gì) được tự động phát hiện và bỏ qua, không bao giờ nhân đôi.

## Liên hệ và hỗ trợ

omega-jail không có giao diện: chức năng **Liên hệ và hỗ trợ** của các công cụ omega khác được thực hiện qua dòng lệnh.

```bash
./omega-jail.sh contact                              # cà phê (PayPal), email và biểu mẫu hỗ trợ
./omega-jail.sh declaration declare --pays FR        # hiển thị thông điệp chính xác, không gửi gì
./omega-jail.sh declaration declare --pays FR --yes
./omega-jail.sh declaration status
./omega-jail.sh declaration withdraw --yes           # không khai báo tôi nữa
./omega-jail.sh version --check                      # phiên bản phát hành mới nhất
```

Việc khai báo là tự nguyện, tắt theo mặc định và chỉ gửi một lần: nó chỉ dùng để đếm số người dùng và, nếu bạn muốn, châu lục hoặc quốc gia của họ (danh sách đóng, không bao giờ là văn bản tự do). Nó gửi một khóa được tạo ngẫu nhiên, tên phần mềm (`omega-jail`) và phiên bản của nó; không bao giờ gửi tên, tên máy, thiết lập, mục tiêu hay kết quả. Địa chỉ IP không được lưu trong các khai báo, nhưng, như mọi lượt truy cập, nó đi qua các kiểm tra bảo mật và nhật ký của máy chủ nhận. `version --check` chỉ đọc danh sách các phiên bản đã phát hành trên trang web; không gửi gì.

## Yêu cầu

- Đã cài `fail2ban` (`fail2ban-client` phải nằm trong `PATH`).
- Một bản cài omega-serv đã có và đã cấu hình (WAF gốc, Active Defense
  và/hoặc phần mở rộng `magnet` phải được bật ở phía omega-serv để các
  jail tương ứng có thể áp dụng).

## Giấy phép

Phân phối theo giấy phép MIT. Xem tệp [LICENSE](../../../LICENSE).
