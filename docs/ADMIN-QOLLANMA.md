# Admin paneldagi yangi imkoniyatlar

`admin` hisobi bilan kiring. Ishchi kalitlarni chatga yubormang; faqat o‘zingiz boshqaradigan serverning admin shakliga kiriting.

## Integratsiyalar

**HEMIS/LMS:** HTTPS tekshirish manzili, talabalar API manzili va kerak bo‘lsa Bearer kalitini kiriting. Ikkala manzil bir domenda bo‘lishi kerak. Saqlashning o‘zi tarmoqqa so‘rov yubormaydi. `Ulanishni tekshirish` HTTP200 JSON javobini tekshiradi. `Talabalarni yangilash` quyidagi moslashtirilgan formatni qabul qiladi:

```json
{"students":[{"hemis_id":"H24011876","full_name":"Sinov Talaba","faculty":"Filologiya","programme":"Özbek tili","course":3,"student_group":"TEST-301","education_form":"Kunduzgi","status":"active"}]}
```

Bu HEMISning barcha versiyalariga universal adapter emas. Universitet API javobi boshqa tuzilishda bo‘lsa, shu maydonlarga moslash kerak. Noto‘g‘ri yozuv bo‘lsa import to‘liq rad etiladi, oldingi lokal baza ishlashda davom etadi. Ulanish uchun ochiq HTTPS domeni kerak; lokal/private/metadata IP, boshqa domenga redirect va URL ichidagi login/parol/query qabul qilinmaydi. TLS tekshiruvi o‘chirilmaydi. Boshlanishida hech qaysi xizmat ulangan deb ko‘rsatilmaydi.

**Telegram:** bot tokenini kiriting va faollashtiring. `Ulanishni tekshirish` faqat Telegram `getMe` orqali botni tekshiradi; hech kimga xabar yubormaydi. Talabaning tasdiqlangan akkauntini bog‘lash, xabar yetkazish va baholash hali alohida bosqich. Bot ulanishini tekshirish xabar almashinuvi to‘liq ishga tushganini anglatmaydi.

Kalit maydoni saqlangandan so‘ng bo‘sh ko‘rinadi. Bo‘sh qoldirish avvalgi kalitni saqlaydi. O‘chirish uchun alohida katakni belgilang. Kalitlar API/HTML/audit jurnalida ko‘rsatilmaydi. SQLite ichida kalitning o‘zi saqlanmaydi; uning yonidagi `*.sqlite3.integration-secrets/` papkasida egasigagina ruxsatli fayllar ishlatiladi. **Bu shifrlash emas.** Windowsda papka ACLlarini, Ubuntu’da xizmat foydalanuvchisini va himoyalangan disk/zaxirani ta’minlang. Bazani zaxiralaganda shu papkani ham himoyalangan tarzda nusxalang. Kalit fayllari Gitdan chiqarib tashlangan.

## Ovozlarni qo‘lda yuklash

**Ovozli chaqiruv** sahifasida har bir til uchun brauzer ovozi yoki yuklangan audio usulini tanlang. MP3 va PCM WAV, eng ko‘pi 5 MB; WAV120 soniyagacha. Ovozlarni bizga yuborish shart emas.

Ikki usul bor:

1. **To‘liq chaqiruv:** masalan25-chi chek va3-operator uchun butun iborani yozib yuklang. Bu aynan shu juftlikka ishlaydi.
2. **Qismlardan yig‘ish:** `Boshlanish` (masalan «A» harfigacha bo‘lgan matn), `Navbat raqami` (masalan25), `Raqamlar orasida` (taklif iborasi), `Operator raqami` (masalan3), `Yakuni`. Tizim besh faylni shu tartibda ketma-ket ijro etadi. Har bir ishlatiladigan navbat/operator raqami uchun kerakli yozuvni yuklang.

Bir tilga yuklangan audio boshqa tilga ishlatilmaydi. To‘liq chaqiruv shu raqamlar uchun qismlardan ustun. Kerakli qismlar yetishmasa, noto‘liq ibora ijro etilmaydi: butun chaqiruv talaba tilidagi brauzer ovoziga o‘tadi. Sinov maydonida yetishmayotgan qismlar ko‘rsatiladi. Bir xil til/qismni yuklash oldingi yozuvni almashtiradi. Kutayotgan chaqiruvlar ketma-ket ovozlashtiriladi.

`Sinov chaqiruvi` orqali tekshiring. TV uchun `START-TV-WINDOWS.bat`ni ishlating; ovoz darajasi tizim sozlamasi hamda Windows/karnayga bog‘liq. Fizik tovush, o‘zbekcha tizim ovozi va Windowsdagi autoplay alohida qurilmada tekshiriladi.

## Til, mavzu va kiosk

Yuqori paneldagi Özbekça / Русский / English interfeys tilini almashtiradi. Tizim atamalari tarjima qilinadi; talabalar ismi, foydalanuvchi yozgan mazmun/izoh/javob va fayl nomlari o‘zicha saqlanadi. Quyosh/oy tugmalari yorug‘/to‘q mavzuni tanlaydi. Tanlovlar shu brauzerda saqlanadi. Til almashtirishda ochiq shakl matnlari va tanlangan fayllar xotirada saqlab tiklanadi; ular doimiy brauzer omboriga yozilmaydi.

Enli Info KeyOS uchun kiosk3 ta yuqori va2 ta pastki kartadan iborat.1024×768 va1280×1024 brauzer o‘lchamlarida barcha5xizmat bo‘limi sahifani aylantirmasdan ko‘rinishi tekshirilgan. Haqiqiy Info KeyOS OS/printer protokoli bu bilan avtomatik tasdiqlanmaydi.

## Excel

Hisobot oynasidagi **Excel yuklab olish** haqiqiy `.xlsx` chiqaradi. Suratdagi12 ustun ishlatiladi: sana, tartib raqami, F.I.Sh., yo‘nalish, kurs, ta’lim shakli, mazmun, kanal, «Ko‘rilgan chora»ning3 bo‘lagi va menejer F.I.Sh. Yuqori sarlavhalar birlashtirilgan, katak chegaralari va matn o‘rash bor. Filtr va tanlangan interfeys tili eksportga qo‘llanadi. Foydalanuvchi matni formula sifatida bajarilmaydi. [Sun’iy ma’lumotli namuna](EXCEL-NAMUNA.xlsx).

## Arizaga fayl biriktirish

Ariza kartasida va amal/javob shakllarida **Fayl biriktirish** bor. Arizaga kirishga vakolati bor menejer, ijrochi, bo‘lim boshlig‘i, direktor va admin ishlatishi mumkin. PDF, DOC/DOCX, XLS/XLSX, TXT, PNG/JPG qabul qilinadi. Har fayl10MB, arizaga10ta va jami50MBgacha. Fayllar SQLite bazada, ariza va audit tarixi bilan saqlanadi. So‘rov takrorlansa, ayni fayl ikkinchi marta qo‘shilmaydi.

Faylni shu arizani ko‘ra oladigan xodimlargina yuklab oladi; public kiosk/TV orqali olish mumkin emas. Arxivda fayllar qoladi; yopilgan arizaga yangi fayl qo‘shilmaydi. Fayl yuklash javob/tasdiqni alohida avtomatik bajarmaydi; keyingi amal xato bo‘lsa yuklangan hujjat arizada saqlanib qoladi.
