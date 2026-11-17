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

Tavsiya etilgan to‘rt qismli tartib: **default.wav → sA.wav → s1.wav → p1.wav**. Harf, navbat raqami va operator chaqiruvga qarab tanlanadi. **Ommaviy yuklash** orqali `s1.wav` dan `s500.wav` gacha birga tanlang; beshta bo‘lim harfi uchun `sA.wav`…`sE.wav`, operatorlar uchun `p1.wav`…`p5.wav` yuklang. MP3 ham shu nomlash tartibida ishlaydi. Yuklash jarayoni natija va xatolarni ko‘rsatadi; to‘xtatilsa oldin saqlangan fayllar qoladi. Bir xil til/qism qayta yuklansa almashtiriladi.

**Namunani o‘rnatish** tugmasi foydalanuvchi yuborgan `default.wav`, `sA.wav`, `s1.wav`, `p1.wav` yozuvlarini o‘zbekcha omborga qo‘shadi va to‘rt qismli tartibni yoqadi. Bu to‘rtta joydagi avvalgi yozuvlarni almashtiradi. Qolgan yozuvlar avtomatik yaratilmaydi.

Avvalgi besh qismli tartib va alohida to‘liq chaqiruv yozuvlari ham mavjud. To‘liq chaqiruvda bo‘lim harfi, raqam va operatorni belgilang.

Bir tilga yuklangan audio boshqa tilga ishlatilmaydi. To‘liq chaqiruv shu raqamlar uchun qismlardan ustun. Kerakli qismlar yetishmasa, noto‘liq ibora ijro etilmaydi: butun chaqiruv talaba tilidagi brauzer ovoziga o‘tadi. Sinov maydonida yetishmayotgan qismlar ko‘rsatiladi. Bir xil til/qismni yuklash oldingi yozuvni almashtiradi. Kutayotgan chaqiruvlar ketma-ket ovozlashtiriladi.

`Sinov chaqiruvi` boshlang‘ich qiymatlari A-001 va 1-operator. Yangi to‘rt qism yuklangan, eski boshlanish qismi bo‘lmasa, mos raqamli tartib taklif qilinadi. Sinov tanlangan tildagi ovoz rejimi va tartibini saqlab, shu sozlamada ishlaydi. Boshqa raqamni sinash uchun uning yozuvini ham yuklang. TV uchun `START-TV-WINDOWS.bat`ni ishlating; ovoz darajasi tizim sozlamasi hamda Windows/karnayga bog‘liq. Fizik tovush, o‘zbekcha tizim ovozi va Windowsdagi autoplay alohida qurilmada tekshiriladi.

## Til, mavzu va kiosk

Yuqori paneldagi Özbekça / Русский / English interfeys tilini almashtiradi. Tizim atamalari tarjima qilinadi; talabalar ismi, foydalanuvchi yozgan mazmun/izoh/javob va fayl nomlari o‘zicha saqlanadi. Quyosh/oy tugmalari yorug‘/to‘q mavzuni tanlaydi. Tanlovlar shu brauzerda saqlanadi. Til almashtirishda ochiq shakl matnlari va tanlangan fayllar xotirada saqlab tiklanadi; ular doimiy brauzer omboriga yozilmaydi.

Enli Info KeyOS uchun kiosk3 ta yuqori va2 ta pastki kartadan iborat.1024×768 va1280×1024 brauzer o‘lchamlarida barcha5xizmat bo‘limi sahifani aylantirmasdan ko‘rinishi tekshirilgan. Haqiqiy Info KeyOS OS/printer protokoli bu bilan avtomatik tasdiqlanmaydi.

## Excel

Hisobot oynasidagi **Excel yuklab olish** haqiqiy `.xlsx` chiqaradi. Suratdagi12 ustun ishlatiladi: sana, tartib raqami, F.I.Sh., yo‘nalish, kurs, ta’lim shakli, mazmun, menejer F.I.Sh., «Ko‘rilgan chora»ning3 bo‘lagi va murojaat qilish usuli. Menejer va murojaat usuli ustunlari o‘rin almashgan Yuqori sarlavhalar birlashtirilgan, katak chegaralari va matn o‘rash bor. Filtr va tanlangan interfeys tili eksportga qo‘llanadi. Foydalanuvchi matni formula sifatida bajarilmaydi. [Sun’iy ma’lumotli namuna](EXCEL-NAMUNA.xlsx).

## Arizaga fayl biriktirish

Ariza kartasida va amal/javob shakllarida **Fayl biriktirish** bor. Arizaga kirishga vakolati bor menejer, ijrochi, bo‘lim boshlig‘i, direktor va admin ishlatishi mumkin. PDF, DOC/DOCX, XLS/XLSX, TXT, PNG/JPG qabul qilinadi. Har fayl10MB, arizaga10ta va jami50MBgacha. Fayllar SQLite bazada, ariza va audit tarixi bilan saqlanadi. So‘rov takrorlansa, ayni fayl ikkinchi marta qo‘shilmaydi.

Faylni shu arizani ko‘ra oladigan xodimlargina yuklab oladi; public kiosk/TV orqali olish mumkin emas. Arxivda fayllar qoladi; yopilgan arizaga yangi fayl qo‘shilmaydi. Fayl yuklash javob/tasdiqni alohida avtomatik bajarmaydi; keyingi amal xato bo‘lsa yuklangan hujjat arizada saqlanib qoladi.


## Beshta bo‘lim va operator

**Sozlamalar** sahifasidagi bo‘lim jadvalida har biriga takrorlanmaydigan harf va operator tanlang. Boshlang‘ich bog‘lanish A/1, B/2, C/3, D/4, E/5. Har bir harf raqamlari alohida yuritiladi. Sozlama yangi cheklarga ta’sir qiladi; avvalgi cheklar o‘z harfi va operatorida qoladi. Demo hisoblar: `manager`, `manager2`, `manager3`, `manager4`, `manager5`. Ishchi hisoblarni Foydalanuvchilar sahifasida yarating.


## Logotiplar va belgilar

Tizim sozlamalaridagi **Logotiplar va interfeys belgilari**dan joyini tanlang, PNG/JPEG yuklang va saqlang. Tizim hamda kiosk logotiplari alohida. Standartga qaytarish faqat tanlangan belgini tiklaydi. Beshta bo‘lim rasmlari **Bo‘lim logotipi** shaklida boshqariladi. Kiosk bosh ekranida yangilanish 10 soniya ichida ko‘rinadi; kabinetni qayta ochganda saqlangan rasmlar yuklanadi.

## Talabalarni o‘zgartirmasdan Excel’dan qo‘shish

Talabalar bazasidagi Excel shaklidan asl faylni tanlang. HEMIS ID bo‘yicha mavjud yozuv o‘zgartirilmaydi. Ism va barcha yettita asl ustun qiymatlari saqlanadi. Takroriy ID yoki noto‘g‘ri qator bo‘lsa butun import bekor qilinadi. Faylda bo‘lmagan guruh, yo‘nalish va tasdiqlangan faol holat taxmin qilinmaydi. Ishchi bazaning zaxirasini saqlang.


## Birinchi admin paroli mos kelmasa

START-WINDOWS.bat endi fayl mavjudligiga emas, bazadagi hisoblar mavjudligiga qaraydi. Bo‘sh baza avvalgi muvaffaqiyatsiz urinishdan qolgan bo‘lsa ham login/parol yaratish takrorlanadi. Parollar mos kelmasa shu oynada qayta kiritiladi. Mavjud hisob/parol o‘zgartirilmaydi. Eski nusxada serverni Ctrl+C bilan to‘xtatib, loyiha papkasida `py -3 navbot\app.py --db navbot\navbot.sqlite3 --init-admin` buyrug‘i bilan birinchi adminni yarating; keyin START-WINDOWS.bat ni oching. Bazani o‘chirmang.

Excel hisobotining yuqorisida universitetning to‘liq nomi, alohida ofis/hisobot sarlavhasi va davr ko‘rsatiladi. To‘q ko‘k fonda 28 punktli universitet nomi, och kulrang-ko‘k ustun sarlavhalari va aniq katak chegaralari qo‘llanadi. Yashil fon olib tashlangan; Excelning bo‘sh katak chiziqlari ham ko‘rinadi. H ustuni — mas’ul menejer; I–K — ko‘rilgan chora; L — murojaat qilish usuli.

## Til va ko‘rinish menyulari

Yuqorida joriy til yozilgan bitta ochiladigan tugma bor. Uni bosib o‘zbekcha,
ruscha yoki inglizchani tanlang. Yonidagi bitta quyosh/oy menyusidan yorug‘ yoki
to‘q ko‘rinishni tanlang. Tanlov keyingi kirishda ham saqlanadi. Escape yoki
menyudan tashqariga bosish menyuni yopadi.

## Murojaatlarni o‘chirish va sinov navbatlarini tozalash

Faqat superadmin foydalanadi. Bitta kartada **Murojaatni o‘chirish**, umumiy
ro‘yxat tepasida **Murojaat va navbatlarni tozalash** tugmalari bor. Tozalash
barcha joriy murojaatlarni, shu jumladan arxivdagilarni qamraydi. Oynada yozuvlar
soni va raqamlari ko‘rsatiladi. Sabab, aynan ko‘rsatilgan son va superadminning
joriy paroli bilan tasdiqlang. Parol urinishlariga mavjud login cheklovi qo‘llanadi.

Talabalar, hisoblar, audio, integratsiya sozlamalari va audit o‘chmaydi. Murojaat
mazmuni, javobi, izohi, ilovalari, jarayon tarixi va bildirishnomalari olib
tashlanadi; ariza/chek identifikatorlari qayta ishlatilmasligi uchun shaxssiz
raqam qaydlari qoladi. Auditda kim, qachon, qaysi raqamlarni, nima sababdan
olib tashlagani saqlanadi. Eski zaxiralardagi nusxalar o‘z saqlash muddatida qoladi.
Bu kriptografik yoki sud-ekspertizaviy o‘chirish kafolati emas.

Ko‘rib chiqish oynasi ochilgandan keyin yaratilgan yangi murojaatlar bu amalga
kirmaydi. Tanlangan yozuvning versiyasi o‘zgarsa, butun amal bekor qilinadi;
oynani yopib, qayta oching. Tizimni yangilashning o‘zi hech narsani tozalamaydi.

Yangilashdan oldin tekshirilgan zaxira oling. Schema7 deleted_at ustunini qo‘shadi;
server qayta yoqilganda o‘chirilgan yozuvlar qayta yaratilmaydi. Zaxira hisobotida
requests jami raqam qaydlarini, active_requests joriy murojaatlarni,
deleted_request_reservations esa olib tashlangan yozuvlarning raqam qaydlarini
ko‘rsatadi. Ishchi o‘chirish amali qaytarilmaydi; zaruratda zaxiradan tiklash
alohida, administrator nazoratidagi jarayon hisoblanadi.
