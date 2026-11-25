# NAVBOT egasi boshqaruvi

Muallif metama’lumoti: **Quvonchbek Rustamov**. Oddiy ekran pastida
`© 2026 ToşDÖTAU` qoladi. HTML author metama’lumoti sahifa manbasidan ko‘rinadi;
bu maxfiy kalit yoki egalikni huquqiy isbotlovchi imzo emas.

Egasi boshqaruvi `/owner` manzilida, universitet xodimlarining hisoblaridan alohida.
Superadmin hisobiga kirish egasi vakolatini bermaydi. Egasi sessiyasi xodimlar
murojaatlariga kirish huquqini ham bermaydi. Standart hisob, parol, yashirin kirish,
avtomatik muddat tugashi yoki tashqi serverdan o‘chirish mexanizmi yo‘q.

## Linux serverda birinchi sozlash

Avval kodni yangilab, web xizmatini qayta ishga tushiring. Egasi hisobini faqat
ishonchli server terminalida yarating (parolni buyruq satri yoki chatga yozmang):

```bash
sudo -u navbot /usr/bin/python3 /opt/navbot/navbot/app.py --db /var/lib/navbot/navbot.sqlite3 --init-owner
```

Egasi loginini, kamida 12 belgili harf/raqamli parolni va tasdiqni kiriting.
Terminalda bir marta ko‘rsatilgan maxfiy kalitni autentifikator ilovasiga
(Google/Microsoft Authenticator va boshqalar; TOTP, 6 raqam, 30 soniya, SHA-1)
qo‘shing. Kalitni xavfsiz oflayn joyda saqlang. Sozlashni ilovadagi kod bilan
tasdiqlang. Sozlash kodi qayta qabul qilinmaydi: kirish uchun keyingi kodni kuting.
Server va telefon vaqti to‘g‘ri/sinxron bo‘lishi kerak.

Brauzerda `https://SIZNING-SERVER/owner` ni oching. Parol va autentifikator kodi
bilan kiring. Ishlab chiqarishda egasi boshqaruvini HTTPS yoki ishonchli SSH
port-forward orqali oching: oddiy HTTP tarmoqdagi parolni himoyalamaydi.
Sessiya 10 daqiqa amal qiladi, HttpOnly/SameSite=Strict cookie orqali saqlanadi;
HTTPS reverse proxy `X-Forwarded-Proto: https` yuborsa Secure ham o‘rnatiladi.
Cookie faqat `/api/owner` yo‘liga yuboriladi. 5 ta noto‘g‘ri urinish 15 daqiqaga
kirish va boshqaruvni cheklaydi. Kirish kodi qayta ishlatilmaydi.

## Vaqtincha to‘xtatish va qayta yoqish

Egasi sahifasida sabab va egasi parolini kiritib tugmani bosing. To‘xtatishda
brauzer qo‘shimcha tasdiq so‘raydi. Amallar va vaqtlar alohida `owner_events`
jurnalida saqlanadi; interfeysda oxirgi 50 tasi ko‘rinadi. Parol/TOTP maxfiy
kaliti jurnalga yozilmaydi. Eskirgan holatdan yuborilgan amal 409 bilan rad etiladi.

To‘xtatilganda oddiy sahifalarda ochiq xizmat to‘xtatilishi xabari, APIlarda
`503 service_suspended` qaytadi. Kiosk, TV, xodimlar, talabalar va HTTP
integratsiyalari ishlamaydi. Ochiq kiosk/TV oynalari keyingi API so‘rovida shu
xabarga o‘tadi; qayta yoqilgach 15 soniyagacha ichida qayta ochiladi.
Egasi sahifasi va uning statik fayllari ochiq qoladi, boshqaruv faqat egasi
sessiyasiga ruxsat etiladi. Telegram worker ham to‘xtash holatini tekshiradi,
navbatdagi xabarlar saqlanadi. Boshlangan HTTP/network amallari tugashi mumkin;
Telegram long-poll to‘xtashdan oldin yuborilgan bo‘lsa 15 soniyagacha davom etishi
mumkin. Murojaatlar, hujjatlar, cheklar, loginlar va konfiguratsiya o‘chirilmaydi.
Qayta yoqishda ular saqlangan holatdan davom etadi.

Alohida ishlayotgan Telegram worker yangi kodni olishi uchun uni ham qayta
ishga tushiring (agar o‘rnatilgan bo‘lsa):

```bash
sudo systemctl restart navbot
sudo systemctl restart navbot-telegram
```

## Hisobni tiklash

Telefon/egasi paroli yo‘qolsa, ishonchli server terminalida:

```bash
sudo -u navbot /usr/bin/python3 /opt/navbot/navbot/app.py --db /var/lib/navbot/navbot.sqlite3 --reset-owner
```

Yangi login, parol va yangi autentifikator kaliti sozlanadi. Eski egasi sessiyalari
bekor bo‘ladi. Xizmatning to‘xtatilgan/faol holati va jurnali saqlanadi. Tiklash
ham jurnalga yoziladi. Xizmat o‘zi avtomatik qayta yoqilmaydi.

## Ishonch chegarasi va shartnoma

Bu mahalliy litsenziya boshqaruvi. Linux root yoki bazaga/kodga to‘g‘ridan-to‘g‘ri
kirishi bor odam nazoratni o‘zgartirishi yoki nusxa olishi mumkin. Buni mutlaq
nusxa ko‘chirish himoyasi yoki kriptografik mualliflik dalili deb ko‘rsatmang.
Egasi kaliti va backupdagi `owner_account` (TOTP kaliti ham bor) ma’lumotlarini
himoyalang. Universitetning foydalanish huquqi, to‘xtatish va ma’lumotlarni olish
shartlari yozma litsenziya/shartnomada belgilanadi. Shartnomaga mos boshqaring.
