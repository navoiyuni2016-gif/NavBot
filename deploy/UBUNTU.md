# Ubuntu server: lokal pilot

Bu buyruqlar maqsad serverda administrator tomonidan bajariladi. Hali serverga hech narsa joylashtirilmadi.

1. `sudo apt-get update && sudo apt-get install -y python3`
2. Alohida tizim foydalanuvchisi: `sudo useradd --system --home /opt/navbot --shell /usr/sbin/nologin navbot` (mavjud bo‘lsa qayta yaratmang).
3. Loyiha fayllarini `/opt/navbot/` ga nusxalang; `navbot/app.py` va `navbot/catalog.json` mavjudligini tekshiring.
4. `sudo install -d -o navbot -g navbot -m 700 /var/lib/navbot`
5. Faqat sun’iy ma’lumotli pilot uchun bazani bir marta `--seed-demo` bilan ishga tushiring:
   `sudo -u navbot python3 /opt/navbot/navbot/app.py --port 8082 --db /var/lib/navbot/navbot.sqlite3 --seed-demo`
   Server ishga tushgach Ctrl+C bosing. Sinov IDlari: `100000000001`, `100000000002`.
6. `sudo install -m 644 /opt/navbot/deploy/navbot.service /etc/systemd/system/navbot.service`
7. `sudo systemctl daemon-reload && sudo systemctl enable --now navbot`
8. `curl --fail http://127.0.0.1:8081/api/catalog` va `sudo systemctl status navbot` bilan tekshiring.

Masofadagi kompyuteringizdan SSH tunnel oching (`USER` va `SERVER`ni almashtiring):

```sh
ssh -N -L 8081:127.0.0.1:8081 USER@SERVER
```

Tunnel ochiq turganda kompyuteringiz brauzerida:

- http://127.0.0.1:8081/kiosk
- http://127.0.0.1:8081/operator?id=1
- http://127.0.0.1:8081/tv
- http://127.0.0.1:8081/tablo?id=1

Har bir jismoniy kiosk/TV kompyuteri uchun tunnel kerak. Hozir portni internetga ochmang:
demo parollar hammaga ma’lum, HTTPS va haqiqiy qurilmalar qabul sinovi hali bajarilmagan. Ommaviy yoki umumiy LAN foydalanishi uchun
kirish nazorati, HTTPS va maqsad server konfiguratsiyasini keyingi bosqichda tayyorlash kerak.
Haqiqiy talabalar ma’lumotlarini hozircha kiritmang. Lokal HEMIS qidiruvi haqiqiy HEMIS API emas.

Yangilashda SQLite bazani o‘chirmang. Zaxira olish yoki almashtirish oldidan xizmatni to‘xtating;
ishga tushirgandan keyin kiosk → chek → operator → TV/tablo → yakunlash oqimini qayta tekshiring.
Loglar: `sudo journalctl -u navbot -n 100 --no-pager`.

Loginlar va yangi ariza oqimi [README](../README.md) da. Demo bazani haqiqiy ishga ishlatmang.
Demo hisoblarsiz birinchi admin: `sudo -u navbot python3 /opt/navbot/navbot/app.py --db /var/lib/navbot/production.sqlite3 --init-admin`.
Service `--db` yo‘lini ayni production bazaga moslang; demo bazani aralashtirmang.
