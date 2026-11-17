# NavBoT — lokal sinov

## Windowsda tez ishga tushirish

1. GitHubda **Code → Download ZIP** ni bosing va ZIPni to‘liq oching.
2. Python 3 o‘rnating; **Add Python to PATH** belgisini yoqing.
3. `START-WINDOWS.bat` faylini ishga tushiring va oynani ochiq qoldiring.
4. Brauzerda `http://127.0.0.1:8081/kiosk`, `/operator?id=1`, `/tv`, `/tablo?id=1` yo‘llarini oching.
5. Talaba qidiruvi uchun `100000000001` yoki `100000000002` sinov IDlarini kiriting.

Batafsil yo‘riqnoma: [WINDOWS.txt](WINDOWS.txt).

ZIPdagi birinchi bosqich kodi `navbot/` ichida. Python 3 standart kutubxonasi ishlatiladi; ilova uchun tashqi paket kerak emas.

## Ishga tushirish

```sh
cd /workspace/NavBot
python3 navbot/app.py --port 8081 --db /tmp/navbot-local.sqlite3
```

Lokal brauzer yo‘llari: `/kiosk`, `/operator?id=1`, `/tv`, `/tablo?id=1`.
TVda ovozni tugma bilan yoqish kerak. Ovoz sifati va o‘zbekcha ovoz mavjudligi brauzer/operatsion tizimga bog‘liq.
Server faqat loopback interfeysida ishlaydi. Birinchi bosqichda autentifikatsiya yo‘q; uni tashqi tarmoqqa ochmang.
SQLite fayli navbat holatini saqlaydi. Testlarni alohida baza bilan bajaring.

## Brauzer regressiya sinovi

Playwright va Chromium mavjud muhitda, bo‘sh sinov bazasidagi serverga qarshi:

```sh
NAVBOT_URL=http://127.0.0.1:8081 node tests/queue-browser.cjs
```

Sinov uch tilda chek, chop etish tugmasi, navbat, chaqirish/qayta chaqirish,
operator qabuli, TV, tablo va qabulni yakunlashni tekshiradi.
Speech APIga til/matn uzatilishi tekshiriladi; haqiqiy ovoz va printer tekshirilmaydi.

## Keyingi bosqich

Word texnik talabining 0.5-versiyasi arxivda yo‘q. Uni olgach menejer autentifikatsiyasi,
profil paroli, serverdagi rol huquqlari, HEMIS lokal sinov bazasi va murojaatlarni
muddat/sabab bilan yo‘naltirish qoidalarini hujjatga mos ravishda kiritish kerak.
Menejer, rollar va yo‘naltirish hali amalga oshirilmagan. Operator uchun lokal HEMIS ID qidiruvi qo‘shilgan.

## Lokal HEMIS qidiruvi

`--seed-demo` parametri sun’iy talabalarni qo‘shadi (mavjudlarini almashtirmaydi).
Sinov IDlari: `100000000001`, `100000000002`. Operator oynasidagi HEMIS ID maydonidan qidiring.
Bu haqiqiy HEMIS integratsiyasi emas; ma’lumot kiosk/TV/tabloda ko‘rsatilmaydi.
Sinov: `node tests/student-browser.cjs`. Ubuntu yo‘riqnomasi: [deploy/UBUNTU.md](deploy/UBUNTU.md).
