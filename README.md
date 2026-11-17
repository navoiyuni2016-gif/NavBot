# NavBoT — v0.5 lokal ishchi sinov

ToshDO‘TAU Registrator ofisi: navbat, murojaatlar reyestri va ijro nazorati.
Talab manbasi: [0.5 hujjati](docs/requirements-v0.5.txt). Kiosk, TV, tablo va kabinetlar navy/teal dizayn namunalariga moslashtirilgan.

## Windowsda ishga tushirish

1. GitHubda **Code → Download ZIP** ni bosing; ZIPni to‘liq yangi papkaga oching.
2. [Python 3.12 yoki yangiroq](https://www.python.org/downloads/windows/) o‘rnating; **Add Python to PATH** ni belgilang.
3. `START-WINDOWS.bat` faylini oching. Server oynasini yopmang.
4. Chrome yoki Edge brauzerida quyidagi manzillarni oching.

| Oyna | Manzil |
| --- | --- |
| Kiosk | http://127.0.0.1:8081/kiosk |
| Xodim kirishi | http://127.0.0.1:8081/login |
| Menejer/operator | http://127.0.0.1:8081/operator |
| TV | http://127.0.0.1:8081/tv |
| 1-oyna tablosi | http://127.0.0.1:8081/tablo?id=1 |

**Faqat lokal sinov hisoblari** (`--seed-demo` bilan yaratiladi):

| Login | Rol |
| --- | --- |
| `admin` | Superadmin |
| `manager` | 1-operator menejeri |
| `manager2` | 2-operator menejeri |
| `manager3` | 3-operator menejeri |
| `manager4` | 4-operator menejeri |
| `manager5` | 5-operator menejeri |
| `executor` | O‘quv bo‘limi ijrochisi |
| `head` | O‘quv bo‘limi boshlig‘i |
| `director` | Direktor / umumiy hisobot |

Hammasining dastlabki sinov paroli: `Navbot-Test-2026!`. O‘zgartirilgan parol qayta ishga tushirganda tiklanmaydi.
Talaba sinov IDlari: `100000000001`, `100000000002`, `H24011876`. Bular haqiqiy talabalar emas.
Profil orqali parol almashtirilganda barcha sessiyalar yopiladi, yangi parol bilan qayta kiring.


## Dialogsiz avtomatik chek (Windows kiosk)

80 mm printer drayverini o‘rnating va Windows **Settings → Printers & scanners** ichida uni **Default printer** qiling. Windowsning avtomatik default printer tanlashini o‘chiring; qog‘oz o‘lchami 80 mm ekanini printer sozlamasida tekshiring. Avval Windows test sahifasini chiqarib ko‘ring.

Oddiy Chrome tabini ishlatish o‘rniga **START-KIOSK-WINDOWS.bat** faylini oching. U lokal serverni kerak bo‘lsa ishga tushiradi va alohida NavBoT Chrome profilini `--kiosk-printing --kiosk` bilan ochadi. Katalogdagi xizmat bosilganda bitta chek yaratiladi va `window.print()` avtomatik chaqiriladi; kiosk rejimi chop etish dialogini avtomatik tasdiqlaydi. Qayta chop etish ayni raqamni ishlatadi. Kioskdan chiqish: **Alt+F4**.

Oddiy brauzerda avtomatik print dialogi chiqadi; dialogsizlik faqat maxsus Chrome kiosk oynasida ishlaydi. Printer mavjud bo‘lmasa yoki PDF destination tanlangan bo‘lsa qog‘oz chiqmaydi. Ilova brauzerdan printerning fizik muvaffaqiyatini bila olmaydi; qog‘oz, drayver va default printerni tekshiring. Windows Chrome va haqiqiy printerdagi dialogsizlik bu Linux muhitida tekshirilmagan.

## Linux/macOS

Ilova Python standart kutubxonalarida ishlaydi, tashqi paket kerak emas:

```sh
cd /workspace/NavBot
python3 navbot/app.py --port 8081 --db navbot/navbot.sqlite3 --seed-demo
```

Bu loopbackdagi lokal pilot. Jismoniy kiosk/TV, umumiy LAN va tashqi HTTPS uchun [Ubuntu yo‘riqnomasi](deploy/UBUNTU.md) va haqiqiy uskunalarda alohida qabul sinovi kerak.

## Ishchi jarayon

Kioskda til → bo‘lim → xizmat → chek. Menejer o‘z loginida navbatni chaqiradi; TV va tegishli tablo yangilanadi. Qabulni boshlash TVning xizmat ko‘rsatilmoqda qismiga juftlik qo‘shadi. Qabulni tugatish jismoniy navbatni tugatadi; **ariza alohida saqlanadi**.

Menejer HEMIS ID bilan talabani topib arizaga biriktiradi, mazmun/izohni saqlaydi. Joyida hal qilish yoki muddat va ichki asos bilan mas’ulga yuborish mumkin. Ijrochi sabab bilan menejerga qaytaradi yoki javobni tasdiqqa yuboradi. Bo‘lim boshlig‘i tasdiqlaydi yoki izoh bilan tuzatishga qaytaradi. Qayta yo‘naltirishda raqam va amaldagi muddat saqlanadi. Faqat vakolatli rahbar muddatni sabab bilan o‘zgartiradi; tarixda oldingi/yangi sana va asos qoladi.

Telefon orqali murojaatni menejer talaba shaxsini tasdiqlaganini belgilab kiritadi; unga chek, kiosk navbati yoki TV chaqiruvi yaratilmaydi. Bu belgi avtomatik shaxs tasdig‘i emas: universitet tasdiqlash tartibini belgilashi kerak.

Hisobot bazadagi yozuvlardan hisoblanadi. Filtrlar, bo‘limlar kesimi, arxiv, suratdagi shaklda haqiqiy XLSX va UTF-8 CSV eksport mavjud. Tashqi jadvalga eksportda formula kiritish himoyasi ishlaydi.

## Saqlash va yangilash

Baza `navbot/navbot.sqlite3` ichida; integratsiya kalitlari uning yonidagi `.integration-secrets` papkasida (himoyalangan zaxiraga uni ham qo‘shing); o‘chirmang yoki yangi ZIP bilan almashtirmang. Serverni Ctrl+C bilan to‘xtatib yangilang. Birinchi v0.5 migratsiyasidan oldin SQLite backup API orqali `.pre-v05-….bak` nusxasi olinadi. Oldingi chek/student/call yozuvlari qoladi. Eski cheklarda vaqt bo‘lmagan: import vaqtini haqiqiy qabul vaqti deb qabul qilmang, tarixda `legacy_import` belgisi bor.

Bazani ko‘chirish/zaxiralash: serverni to‘xtating, `.sqlite3`, mavjud bo‘lsa `.sqlite3-wal` va `.sqlite3-shm` fayllarini birga saqlang yoki SQLite backup API ishlating. Qaytishda eski kod va unga mos to‘liq baza zaxirasini birga tiklang; ishlayotgan bazani qisman almashtirmang.

Demo hisoblarsiz birinchi admin yaratish:

```sh
python3 navbot/app.py --db navbot/production.sqlite3 --init-admin
```

Login/parol terminalda kiritiladi. Keyin ayni baza bilan `--init-admin` va `--seed-demo`siz serverni ishga tushiring. Vaqtinchalik parol birinchi kirishda almashtiriladi. Demo bazani ishlab chiqarish bazasi sifatida ishlatmang.

## Talabalar fayli

Superadmin paneli orqali JSON fayldan yuklash (1–10000 yozuv). Misol:

```json
{"students":[{"hemis_id":"H24011876","full_name":"Sinov Talaba","faculty":"Filologiya","programme":"Özbek tili","course":3,"student_group":"TEST-301","education_form":"Kunduzgi","status":"active"}]}
```

Import HEMIS ID bo‘yicha yangilaydi/qo‘shadi. Bir xato bo‘lsa butun import qaytariladi; oldingi ma’lumotlar saqlanadi. Qidiruv internetga bog‘liq emas.

## Tekshirish

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Bu testlar vaqtinchalik bazalarda haqiqiy HTTP server hamda SQLite bilan autentifikatsiya, vakolat, parallel holat versiyasi, ariza oqimi, import, hisobot va migratsiyani tekshiradi.

Playwright va Chromium o‘rnatilgan muhitda, alohida bo‘sh demo bazasidagi serverga qarshi:

```sh
NAVBOT_URL=http://127.0.0.1:8081 node tests/queue-browser.cjs
NAVBOT_URL=http://127.0.0.1:8081 node tests/student-browser.cjs
node tests/enhancements-browser.cjs
```

Ovoz testlari Speech APIga til/matn yuborilishini tekshiradi. Haqiqiy karnay, Windowsdagi ovozlar, 80 mm printer va Info KeyOS ushbu avtomatik testlarga kirmaydi.

## Admin sozlamalari va qolgan ishlar

Admin paneldan integratsiya URL/kalitlarini saqlash va ulanishni tekshirish, mos formatdagi LMS talabalarini yuklash hamda uch tilda MP3/WAV chaqiruv yozuvlarini boshqarish mumkin. Tashqi ulanishlar dastlab sozlanmagan; hech biri tekshiruvsiz ulangan deb ko‘rsatilmaydi. Telegram tekshiruvi botni aniqlaydi, lekin talaba xabarlari/baholashni o‘zidan-o‘zi yoqmaydi. Haqiqiy HEMIS API tuzilmasi boshqacha bo‘lsa adapter kerak.

Kabinetlar3til va yorug‘/to‘q mavzuda ishlaydi; enli kiosk3+2 kartali; Excel eksporti suratdagi jadval shaklida. Ariza/javobga fayl qo‘shiladi va vakolatli xodimlar yuklab oladi. [Batafsil admin qo‘llanmasi](docs/ADMIN-QOLLANMA.md).

Yakuniy ariza shablonlari, tasdiqlangan xizmat/rol/muddat matritsasi va huquqiy asoslar hali berilmagan. Hozirgi rollar oldindan belgilangan. Cheklanmagan rol konstruktorlari, dinamik shablon dizayneri va qurilma protokollari qolgan. Tasdiqlangan Telegram akkaunt bog‘lash, javob/baho yetkazish va LMSdan ariza/holat/javob/baho almashinuvi hali bajarilmagan.

Qabul dalillari va talablar qamrovi: [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md).

## Ekranlardan namuna

![TV](docs/previews/tv.png)

[Kiosk](docs/previews/kiosk.png) · [Menejer](docs/previews/manager.png)

## TV avtomatik ovozi

TVda ovozni yoqish/o‘chirish tugmasi yo‘q; yangi chaqiruvlar talaba tanlagan tilda avtomatik ovozlashtiriladi. Windowsda **START-TV-WINDOWS.bat** faylini oching: alohida Chrome TV profili `--autoplay-policy=no-user-gesture-required --kiosk` bilan ishga tushadi. Bu maxsus TV oynasi uchun; oddiy brauzer avtomatik ovozni cheklashi mumkin. TV oynasidan chiqish: Alt+F4. Ovoz darajasini Superadmin sozlamasi va Windows/karnaydan belgilang. Haqiqiy Windows/karnayda alohida tekshirish zarur.


### Beshta yo‘nalish va yozib olingan chaqiruvlar

Superadmin → Sozlamalar sahifasida beshta bo‘limning harfi va operatorini alohida belgilang. Boshlang‘ich tartib A/1, B/2, C/3, D/4, E/5. Har bir harf mustaqil raqamlanadi: A-001, B-001. O‘zgartirish yangi cheklarga qo‘llanadi; mavjud chek raqami va operatori saqlanadi. Menejer faqat o‘z operatoriga kelgan kiosk murojaatini qabul qiladi.

Superadmin → Ovozli chaqiruv → Ommaviy yuklash: `default.wav`, `sA.wav`…`sE.wav`, `s1.wav`…`s500.wav`, `p1.wav`…`p5.wav` fayllarini birga tanlang. Harflarni o‘zgartirsangiz, mos `sX.wav` yozuvini yuklang. Tartib: **default → harf → raqam → operator**. MP3 ham qabul qilinadi. Har bir fayl 5 MB gacha, umumiy audio ombori 200 MB.

Yuborilgan to‘rtta asl yozuv `navbot/voice/uz` ichida. Ovoz sahifasidagi namunani o‘rnatish tugmasi ularni o‘zbekcha ovoz omboriga yozadi va to‘rt qismli tartibni yoqadi. Boshqa harf/raqam/operator yozuvlarini o‘zingiz yuklaysiz. Yetishmagan yozuv bo‘lsa, butun chaqiruv tanlangan tilda brauzer ovozi orqali aytiladi.
