# NAVBOT — universitetlar uchun sotuv va tenant paketi

Muallif: Quvonchbek Rustamov. Har bir universitet — alohida **tenant**:
alohida domen, Linux foydalanuvchisi, Python jarayoni, SQLite bazasi, fayllar,
HEMIS/Telegram kalitlari, xodimlar, egasi hisobi va backup. Umumiy dastur kodi
faqat o‘qiladi. Bu bitta bazaga `tenant_id` qo‘shilgan SaaS emas; har bir
universitet jarayon va operatsion tizim foydalanuvchisi orqali ajratilgan.
Bitta tenantni to‘xtatish boshqalarning xizmatini to‘xtatmaydi.

**Hozirgi /opt/navbot va /var/lib/navbot o‘rnatmasini ko‘chirmang/o‘chirmang.**
Unga tegishli eski navbot.service o‘z holicha qoladi. Yangi paketni alohida
root-owned release papkasiga joylang. Birinchi pilotni ishlab turgan universitet
bilan bir bazada sinamang. Har bir domenda o‘z HTTPS sertifikati bo‘lsin.

## Paket tarkibi

- `navbot/`: server, kiosk, TV, dashboard, hujjatlar va egasi boshqaruvi.
- `sales/tenant.py`: tenant rejasi, yangi bo‘sh baza, Ubuntu/systemd/Nginx
  o‘rnatish va aynan shu tenantning tekshiriladigan backupi.
- `sales/examples/`: A/B universitetlar uchun uch tildagi konfiguratsiya namunalari.
- `sales/COMMERCIAL-OFFER.md`: mijozga beriladigan tijorat taklifi namunasi.
- `sales/DELIVERY-CHECKLIST.md`: topshirish va qabul qilish ro‘yxati.
- `sales/LICENSE-TERMS.md`: yurist bilan yakunlanadigan litsenziya shartlari.
- `deploy/`: printer/TV vositalari va operatsion yo‘riqnomalar.
- `PACKAGE-MANIFEST.json`, tashqi `.sha256`: paket yaxlitligi tekshiruvi.

Paketda mijoz bazalari, shaxsiy audio/logotiplar, loginlar, egasi kalitlari,
Telegram/LMS tokenlari va backup arxivlari bo‘lmaydi. Demo misollari soxta.
Standart login/parol yoki egasi kaliti yaratilmaydi.

## Talablar

Ubuntu 24.04+, Python 3.12+, Nginx, systemd, certbot. DNS domen/subdomeni
serverga yo‘naltiriladi. Port 80/443 tashqaridan; backendlar **faqat loopback**.
Root/operator barcha tenantlarga ishonchli: rootdan mutlaq ajratish uchun
universitetlarga alohida VM/server ajrating. Yuk ko‘tarish sig‘imi bu paket uchun
benchmark qilinmagan; pilotda real xodim/kiosklar bilan o‘lchang.

## 1. Root-owned release va universitet konfiguratsiyasi

ZIPni tekshiring va yangi papkaga oching; masalan `/opt/navbot-sales/2026-11-25`.
Barcha release fayllari va parent papkalar root-owned, group/world-writable bo‘lmasin.
Kod release papkasiga universitetning bazasi yoki maxfiy fayllarini qo‘ymang.

```bash
sudo apt-get install python3 nginx certbot
sudo mkdir -p /opt/navbot-sales/2026-11-25
sudo unzip NAVBOT-SALES.zip -d /opt/navbot-sales/2026-11-25
cd /opt/navbot-sales/2026-11-25/NAVBOT-SALES
python3 sales/build_package.py --verify /PATH/TO/NAVBOT-SALES.zip
```

Misol JSONni **release tashqarisidagi** operator katalogiga nusxalang, id/domain/
port va uch tildagi nomlarni haqiqiy universitetga moslang. ID 2–21 belgili,
lotin kichik harfi bilan boshlanadi. Port 10000–60000, har tenantga boshqa port.
`catalog` ixtiyoriy: hozirgi model 5 bo‘lim × 5 xizmat × 3 til; nomlarni
moslang, cheksiz bo‘limlar soni bu versiyada qo‘llanmaydi. Logotiplar, ovozlar,
xizmatlar va operatorlar keyin shu universitet admini tomonidan sozlanadi.

```bash
python3 sales/tenant.py generate /srv/navbot-plans/a.json --output /srv/navbot-plans/generated
python3 sales/tenant.py generate /srv/navbot-plans/b.json --output /srv/navbot-plans/generated
```

Bir reja katalogida takroriy ID/domain/port rad etiladi. `generate` xizmat,
baza yoki Nginxni o‘zgartirmaydi. `ACCESS.txt` aynan tenantning foydalanuvchisi,
bazasi, login yaratish, qayta kirish va backup buyruqlarini ko‘rsatadi.

## 2. HTTPS tayyorlash va tenantni o‘rnatish

```bash
sudo python3 sales/tenant.py bootstrap /srv/navbot-plans/a.json
sudo certbot certonly --webroot -w /var/www/navbot-acme -d a.REAL-DOMAIN.uz
sudo python3 sales/tenant.py install /srv/navbot-plans/a.json
```

`bootstrap` faqat shu domenning HTTP→HTTPS/ACME vhostini qo‘shadi. Boshqa
saytni o‘chirmaydi, Nginx tekshiruvi muvaffaqiyatsiz bo‘lsa yangi linkni olib,
reload qilmaydi. Sertifikat yo‘q bo‘lsa `install` ish boshlamaydi.

`install` yangi `nb-TENANT` tizim foydalanuvchisi, 0700 data papkasi, 0600 bo‘sh
baza va `/etc/navbot-tenants/TENANT.json` yaratadi. Mavjud tenant/foydalanuvchi/
baza/konfiguratsiyani qayta ishlatmaydi. Konfiguratsiyalarni tekshiradi; xizmatni
avtomatik boshlamaydi. Yarim yo‘lda xato bo‘lsa logni tekshiring: u mavjud
ma’lumotlarni avtomatik o‘chirmaydi, takroriy install esa mavjud targetni rad etadi.

**ACCESS.txt dagi buyruqlar bilan** shu tenantning birinchi universitet adminini
va alohida egasi hisobini yarating. Boshqa tenantdan baza yoki egasi kalitini
nusxalamang. Har bir egasi hisobida o‘z TOTP autentifikatori bo‘ladi.

```bash
sudo systemctl enable --now navbot-university-a.service navbot-university-a-backup.timer
sudo systemctl status navbot-university-a --no-pager
curl -H 'Host: a.REAL-DOMAIN.uz' http://127.0.0.1:18081/api/catalog
```

Xuddi shu tartibda B universitetini boshqa ID/domain/port bilan qo‘shing.
Backend boshqa tenant domenidagi Host so‘rovini **421** bilan rad etadi;
A sessiyasi B bazasida vakolat bermaydi. Cookie domeni host-only; har domen
uchun HTTPS ishlating. Nginxdagi default noma’lum domen siyosatini administrator
tekshirsin; mavjud universitetning default saytini avtomatik almashtirmaymiz.

Telegram uchun har tenantga boshqa bot/token kiriting; keyin kerak bo‘lsa
`navbot-TENANT-telegram.service` ni yoqing. Bir botni ikki workerga bermang.
Mavjud printerni boshqa tenantga o‘tkazishdan oldin native agentdagi server URL va
pairingni almashtiring. `downloads/NAVBOT-NATIVE.zip` hamda `deploy/` yo‘riqnomasi
ishlatiladi; pairing kaliti har tenantda yangidan yaratiladi. TV manzili shu
tenantning `https://DOMAIN/tv` manzili bo‘ladi. Rejada yaratilgan `KIOSK-START.bat`
va `TV-START.bat` shu universitet domeniga bog‘langan Chrome to‘liq ekran
launcherlaridir. Windows qurilmasiga keraklisini ko‘chiring. Printer uchun Windows
default printer va 80 mm qog‘ozni haqiqiy qurilmada tekshiring.

Eski universitetga qat’iy bog‘langan **NAVBOT-TV.apk va eski KIOSK.zip bu sotuv
paketiga kiritilmaydi** va tenant endpointi eski APKni bermaydi. Yangi tenant TVsi
brauzer/Chrome fullscreen orqali ishlaydi. Android APK talab qilinsa, uning domeni
va imzolanishi alohida moslashtirilishi kerak; uni tayyor generic APK deb sotmang.

## Backup, tiklash va yangilash

Har tenantning timeri alohida. Backup vaqtida faqat shu tenant web/Telegrami
qisqa to‘xtaydi; boshqa tenantlar to‘xtatilmaydi. Arxivda data, integratsiya
kalitlari, release kodi va shu tenant konfiguratsiyalari bor; sir sifatida saqlang.
Oxirgi 30 backup saqlanadi. Boshqa serverga shifrlangan oflayn nusxa ham oling.

```bash
sudo python3 sales/tenant.py backup university-a
sudo python3 deploy/navbot-backup.py --verify /var/backups/navbot-tenants/university-a/ARCHIVE.tar.gz
```

Tiklashni avval alohida bo‘sh joyda bajaring. Arxivni `--verify` bilan tekshiring,
`data/navbot.sqlite3` dagi `tenant_instance.tenant_id` kerakli ID ekanini tasdiqlang.
Eski versiya/kalitlar ham tiklanishini hisobga oling. Yangi rollback backup oling;
faqat target tenant web/Telegramini to‘xtating, data papkasini zaxiraga ko‘chiring,
arxivdagi data papkasini o‘rnating, egasini `nb-TENANT:nb-TENANT`, papkani 0700,
fayllarni 0600 qiling. WAL/SHM fayllarini boshqa DB bilan aralashtirmang. Webni
ishga tushiring, login/hujjat/HEMIS va backupni tekshiring, keyin Telegramni yoqing.
**A backupini B ustiga tiklamang.** TLS sertifikati/private key bu arxivga kirmaydi; yangi serverga tiklashda sertifikatni alohida xavfsiz tiklang yoki qayta oling. Installer avtomatik live restore bajarmaydi.

Kod yangilashda yangi root-owned release papkasi tayyorlang. Avval tenantning
backupini oling. Bitta pilot tenant unitlaridagi code pathni yangi releasega
ko‘chiring (`ExecStart`, backup unit va `WorkingDirectory`), systemd-analyze bilan
tekshiring, daemon-reload qilib **faqat shu tenantni** restart qiling. Tekshiruvdan
keyin keyingi tenantlarga o‘ting. Bu paketda avtomatik fleet upgrade va tenantlarni
boshqaradigan umumiy web kabinet yo‘q; boshqaruv CLI/systemd orqali bajariladi.

## Paketni qayta yig‘ish

```bash
python3 sales/build_package.py --output /SAFE-OUTPUT/NAVBOT-SALES.zip
python3 sales/build_package.py --verify /SAFE-OUTPUT/NAVBOT-SALES.zip
```

Allowlist faqat mahsulot manbalari/statik resurslarni oladi; runtime DB, maxfiy
fayllar va generatsiya qilingan mijoz rejalari paketga kirmaydi. SHA-256 yaxlitlik
tekshiruvi kriptografik mualliflik/litsenziya imzosi hisoblanmaydi.
