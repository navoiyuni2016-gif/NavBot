# NAVBOT serverini yakuniy sozlash

Bu paket ishlayotgan tizimni tozalamaydi, demo baza yaratmaydi, bot tokenini
almashtirmaydi va Kerio/Nginx TLS yo‘lini o‘zgartirmaydi. O‘rnatuvchi mavjud
`navbot.service` hisobini systemd orqali aniqlaydi (`navbot-svc` bo‘lishi mumkin).
Xizmatlarning asosiy unit fayllarini almashtirmasdan qayta ishga tushish
drop-inlarini qo‘shadi va boot paytida avtomatik ishlashini yoqadi.

## O‘rnatish

Ishlab turgan serverda har bir buyruqni alohida bajaring:

```sh
sudo git -C /opt/navbot pull --ff-only
sudo systemctl restart navbot navbot-telegram
sudo python3 /opt/navbot/deploy/install-operations.py --alert-chat CHAT_ID --rotate-login-password navbot
```

`CHAT_ID` o‘rniga mas’ul administratorning raqamli Telegram chat ID sini
kiriting. Ushbu administrator oldin botga `/start` yuborgan bo‘lishi kerak.
Talabalar chatlarini ogohlantirish manzili sifatida ishlatmang.

Oxirgi qadamda Linux login uchun yangi parol ikki marta so‘raladi; kiritilayotgan
belgilar ko‘rinmaydi. Parol argument, log yoki NAVBOT sozlamasiga yozilmaydi.
Bu Linux login parolidir; ilovadagi hisob paroli Profil → Parolni almashtirish
orqali alohida boshqariladi. Oshkor bo‘lgan owner autentifikator kaliti ham
avvalgi yo‘riqnomadagi `--reset-owner` bilan mahalliy terminalda qayta yaratiladi;
uni chatga yubormang.

O‘rnatishda birinchi zaxira uchun ikki yozuvchi xizmat faqat nusxa olinayotgan
vaqtda to‘xtaydi, so‘ng avvalgi holatiga qaytadi. Siqish va tiklash sinovi
xizmatlar qayta ishga tushganidan keyin bajariladi. Zaxira hajmiga qarab bu
bir necha daqiqa davom etishi mumkin. Xato bo‘lsa o‘rnatuvchi muvaffaqiyat deb
ko‘rsatmaydi; ma’lumotlar bazasi ustiga hech narsa yozmaydi.

## Nima avtomatlashtiriladi

- Har kuni 03:00 Asia/Tashkent (+0–10 daqiqa): baza, hujjat/audio/logo BLOBlari,
  xususiy token fayllari, kod va xizmat/proksi konfiguratsiyasi zaxiralanadi.
  SQLite yaxlitligi, yozuv sonlari va barcha fayllarning SHA-256 qiymati
  ajratilgan katalogda tekshirilgandan keyingina arxiv tayyor deb e’lon qilinadi.
  Oxirgi 30 arxiv saqlanadi.
- Birinchi o‘rnatishda funksional tiklash: arxiv nusxasi alohida vaqtinchalik
  katalogga ochiladi. Non-root foydalanuvchi ostida faqat loopback portida ilova
  ishga tushadi. Faqat nusxada bir martalik test admin yaratiladi. Login,
  murojaatlar ro‘yxati, sozlamalar, Mini App sahifasi va mavjud bo‘lsa bir faylning
  yuklangan baytlari tekshiriladi. Asl baza o‘zgarmaydi; Telegram worker ochilmaydi.
- Har 5 daqiqada: sayt va Telegram xizmatlari, backup timer, HTTP javob,
  Telegram polling yangiligi, diskdagi bo‘sh joy, oxirgi tasdiqlangan zaxira yoshi,
  baza/token fayllari ruxsatlari va parol yangilashi kutilayotgan faol hisoblar.
- O‘rnatishda faqat o‘qish rejimida xavfsizlik auditi: faol hisoblarda ma’lum
  demo paroli qolganmi va owner MFA sozlanganmi. Natijada ism, login, hash yoki
  parol chiqmaydi. Demo parolidagi hisob bo‘lsa monitoring jiddiy ogohlantiradi;
  admin bu hisobni yangilashi yoki faolsizlantirishi kerak. Hisoblar o‘zboshimcha
  o‘chirilmaydi. Tuzatilgandan keyin auditni yangilang:

  ```sh
  sudo python3 /opt/navbot/deploy/navbot-security-check.py --refresh
  sudo systemctl start navbot-monitor.service
  ```
- SSL: `navbot.tsuull.uz` nomi tekshirilib, TLS ulanishi Kerio
  `172.20.4.254:443` orqali bajariladi. Sertifikat muddati 30 kun qolganida
  ogohlantirish, 7 kun qolganida jiddiy signal; ishonch/ulanish xatosi ham signal.
  Mavjud sertifikat avtomatik almashtirilmaydi: u Kerioda boshqariladi.
- Mas’ul Telegram chatiga faqat operatsion holat yuboriladi. Talaba ismi,
  HEMIS ID, murojaat matni, fayl yoki token yuborilmaydi. Bir xil holat 6 soatda
  bir eslatiladi; holat almashsa yangi xabar, barcha tekshiruvlar tiklansa tiklanish
  xabari keladi. Telegramning o‘zi ishlamasa mahalliy jurnal va panel saqlanadi;
  Internet tiklangach xabar keyingi tekshiruvda qayta uriniladi.
- Administrator → Integratsiyalar → Xizmat nazorati: oxirgi monitoring va
  tekshiruvlar ko‘rinadi. 15 daqiqadan eski natija yangi deb ko‘rsatilmaydi.

## Serverdan tashqari zaxira

Mahalliy arxiv host/diski yo‘qolishidan himoya qilmaydi. Alohida server yoki
himoyalangan saqlagich mount qilingandan keyin o‘rnatuvchini qayta ishga tushiring:

```sh
sudo python3 /opt/navbot/deploy/install-operations.py --offsite-dir /mnt/navbot-backups
```

Mavjud chat ID va TLS sozlamalari saqlanadi. Manzil haqiqiy mount bo‘lishi
shart: mount yo‘qolsa lokal katalogga yashirin yozilmaydi. Nusxa vaqtinchalik
faylga yozilib, `fsync` va SHA-256 solishtirishdan so‘ng nashr qilinadi. Tashqi
arxivlar ham 0600; lokal va tashqi joyda 30 tadan avtomatik arxiv saqlanadi.
Tashqi serverga shifrlangan ulanish va saqlagichdagi shifrlashni administrator
ta’minlaydi. Mount berilmaguncha panel va ogohlantirishda bu kamchilik ochiq turadi.

Tashqi manzilni qo‘lda o‘zgartirganda `/etc/navbot/operations.json` va backup
unitning `ReadWritePaths` ruxsati mos bo‘lishi lozim; o‘rnatuvchi buni bajaradi.
Bu fayl root-only. Ichiga bot tokenini yoki parolni yozmang.

## Tekshirish va keyingi tiklash sinovi

```sh
sudo systemctl list-timers navbot-backup.timer navbot-monitor.timer --no-pager
sudo journalctl -u navbot-monitor.service -n 15 --no-pager
sudo cat /var/lib/navbot/operations/status.json
sudo python3 /opt/navbot/deploy/navbot-restore-drill.py --archive /var/backups/navbot/ARXIV.tar.gz --run-as navbot-svc
```

Oxirgi buyruqda haqiqiy arxiv nomi va mavjud non-root xizmat hisobi ishlatiladi.
To‘liq host halokati mashqi uchun alohida staging serverda xizmatlar,
konfiguratsiya, tarmoq va TLS ham tiklanishi kerak. Loopback sinovi yangi
Proxmox hostini tiklash yoki haqiqiy telefon/printerni tekshirish o‘rnini bosmaydi.

## Tekshiruv dalillari va jonli chegaralar

Repozitoriy testlari talaba → xodim → tasdiq → faqat ruxsatli javob/fayl oqimini,
talabalar orasidagi izolyatsiyani, xodim rollarini, parol va sessiya bekor
qilinishini tekshiradi. Telegram transporti soxta API bilan sinovdan o‘tadi;
haqiqiy chatlarga test murojaatlari yuborilmaydi. Foydalanuvchi ishlayotgan
Telegramni tasdiqlagan. Jonli serverga o‘rnatish va xabarning administratorga
yetib borishi faqat serverdagi o‘rnatuvchi bajarilgandan keyin tasdiqlanadi.

Serverni masofadan dalilsiz qayta yuklamang. `enable` va `Restart=on-failure`
tayyorlanadi; haqiqiy elektr uzilishi/reboot mashqi alohida nazorat ostida qilinadi.
