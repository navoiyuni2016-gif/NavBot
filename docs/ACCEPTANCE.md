# v0.5 lokal sinov dalillari — 2026-11-17

Bu hujjat butun texnik talab yakunlanganini anglatmaydi. Quyidagi lokal funksiyalar bajarildi; tashqi xizmatlar va qolgan modullar alohida ko‘rsatilgan.

| Talab | Bajarilgan va tekshirilgan |
| --- | --- |
| 2–3: kiosk, chek, mazmun | 5×5 katalog, uch til, serverda takror kalitga bitta chek/ariza, chop etish/qayta chop etish, xizmat nomining nusxasi, vaqt |
| 4.1: HEMIS ID | Lokal SQLite/fayl importi, raqamli va H-prefiksli ID, F.I.Sh./yo‘nalish/kurs/ta’lim shakli, arizaga biriktirish |
| 4.2–4.4: ijro | Menejerda saqlash/joyida hal qilish, mas’ulga topshirish, sabab bilan qaytarish, amaldagi muddatni saqlab qayta topshirish, javob/tasdiq/tuzatish/yopish |
| 5: muddat | UTC saqlash, Toşkentda ko‘rsatish, qayta ochilganda hisoblash, sariq chegara, kechikish, rahbar muddat o‘zgartirish tarixi. Huquqiy qoidalar tasdiqlanmagan |
| 6: EDO | Yangi/biriktirilgan/yuborilgan/qaytarilgan/yaqin/o‘tgan/tasdiq/arxiv filtrlari, talaba/izoh/javob/tarix |
| 7: hisobot | Saqlangan reyestr, sana/bo‘lim/menejer/xizmat bo‘limi/kanal/holat filtrlari, kunlar dinamikasi, bo‘limlar kesimi, CSV, arxiv |
| 8: Superadmin | Xodim yaratish, vaqtinchalik parol, mavjud rollar; katalog/tarjima/TV/ovoz parametrlarini saqlash. Cheklanmagan rol/shablon konstruktorlari hali yo‘q |
| 10: talabalar | JSON fayldan atomar import va HEMIS ID bo‘yicha yangilash, offline lokal qidiruv; LMS ulanmagan |
| 11–13: TV/tablo/tillar | Chap chaqiruv, o‘ng xizmat, past kutish; qabulda qo‘shish/yakunida chiqarish; 3 miltillash; tanlangan chek/ovoz tili; TV tili alohida |
| 14: shaxsiy kabinet | Login, xeshlangan parol, sessiya, joriy parol bilan yangilash, resetda vaqtinchalik parol va sessiyalarni bekor qilish |
| 15: sozlamalar | Uch tilda nomlar/chek pastki matni/ovoz/TV sarlavhalari, oldindan ko‘rish, PNG/JPEG logo yuklash va kioskda yangilash |
| 18: saqlash | Eski baza migratsiyasi va qayta tiklanadigan migratsiyadan oldingi nusxa; yo‘riqnomada yangilash/qaytish tartibi |

## Bajarilgan tekshiruvlar

- `python3 -m unittest discover -s tests -p 'test_*.py' -v`: 22 ta muvaffaqiyatli test.
- `node tests/workflow-browser.cjs`: bo‘sh vaqtinchalik bazada to‘liq Chromium UI zanjiri; sahifa JS xatolari yo‘q.
- `node tests/queue-browser.cjs`: 3/3 til, chek/vaqt/qayta chop etish, chaqirish/qayta chaqirish/miltillash/qabul/yakunlash, TV/tablo, TV joylashuvi va shaxsiy ma’lumot ko‘rinmasligi.
- `node tests/student-browser.cjs`: login bilan topish/topilmaslik/noto‘g‘ri ID, maydonni pollingda saqlash.
- Admin sozlamasi, chek oldindan ko‘rish va PNG logoni kioskda ko‘rsatish haqiqiy Chromium oynasida tekshirildi.
- CP1251 standarti takrorlangan testda UTF-8 katalog to‘g‘ri ochiladi. Windowsning o‘zida ushbu versiya hali ishga tushirilmagan.

## Qolgan ishlar va qabul cheklovlari

- Telegramga tasdiqlangan talaba akkauntini bog‘lash, javob/baho 1–5, yuborilmagan xabarlar navbati: bot va identifikatsiya shartnomasi bilan keyingi bosqich. Hozir panel ichida davriy olinadigan xabarlar bor; bu haqiqiy Telegram/OS push emas.
- LMSdan ariza/talaba/holat/javob/baho almashish, tashqi ID deduplikatsiyasi va qo‘lda sinxronizatsiya: API manzili, maydonlari va ruxsatlari kerak. Ulangan deb ko‘rsatilmaydi.
- Katalogni 5×5 dan cheklanmagan yaratish/tartiblash, ixtiyoriy rollar va vakolat matritsasi, bo‘lim boshlig‘ining delegatsiyasi, dinamik ariza shablonlari va fayl ilovalari versiyasi hali bajarilmagan. Yakuniy 19-bo‘lim matritsalari ham berilishi kerak.
- Xodim kabinetlarining to‘liq ruscha/inglizcha tarjimasi hali yo‘q; kiosk/chek/ovoz uch tilda. TV interfeys tili alohida sozlanadi.
- Haqiqiy 80mm printer, ovozning eshitilishi, uzbekcha tizim ovozi, Info KeyOS/LED protokoli, boot/kiosk rejimi, printer xatosini qurilmadan olish tekshirilmagan. Hozir brauzer print dialogi ishlatiladi.
- LAN/WAN, HTTPS, ishchi server/subdomen, zaxiradan real operatsion qaytish, tarmoq uzilishi/tiklanishi, qurilma dasturini yangilash — haqiqiy infratuzilmada qabul qilinadi. Ubuntu yo‘riqnomasi tayyor, lekin serverga o‘rnatilmadi.

## Ko‘rinishlar

Bular sun’iy ma’lumotli ishlayotgan ilovadan olingan; dizayn maketi emas.

- [Kiosk](previews/kiosk.png)
- [TV](previews/tv.png)
- [Menejer](previews/manager.png)
