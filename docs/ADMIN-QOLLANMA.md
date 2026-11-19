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

Hisobot oynasidagi **Excel yuklab olish** haqiqiy `.xlsx` chiqaradi. Suratdagi12 ustun ishlatiladi: sana, tartib raqami, F.I.Sh., yo‘nalish, kurs, ta’lim shakli, mazmun, qabul qilgan xodim F.I.Sh., «Ko‘rilgan chora»ning3 bo‘lagi va murojaat qilish usuli. Menejer va murojaat usuli ustunlari o‘rin almashgan Yuqori sarlavhalar birlashtirilgan, katak chegaralari va matn o‘rash bor. Filtr va tanlangan interfeys tili eksportga qo‘llanadi. Foydalanuvchi matni formula sifatida bajarilmaydi. [Sun’iy ma’lumotli namuna](EXCEL-NAMUNA.xlsx).

## Arizaga fayl biriktirish

Ariza kartasida va amal/javob shakllarida **Fayl biriktirish** bor. Arizaga kirishga vakolati bor menejer, ijrochi, bo‘lim boshlig‘i, direktor va admin ishlatishi mumkin. PDF, DOC/DOCX, XLS/XLSX, TXT, PNG/JPG qabul qilinadi. Har fayl10MB, arizaga10ta va jami50MBgacha. Fayllar SQLite bazada, ariza va audit tarixi bilan saqlanadi. So‘rov takrorlansa, ayni fayl ikkinchi marta qo‘shilmaydi.

Faylni shu arizani ko‘ra oladigan xodimlargina yuklab oladi; public kiosk/TV orqali olish mumkin emas. Arxivda fayllar qoladi; yopilgan arizaga yangi fayl qo‘shilmaydi. Fayl yuklash javob/tasdiqni alohida avtomatik bajarmaydi; keyingi amal xato bo‘lsa yuklangan hujjat arizada saqlanib qoladi.


## Beshta bo‘lim va operator

**Sozlamalar** sahifasidagi bo‘lim jadvalida har biriga takrorlanmaydigan harf va operator tanlang. Boshlang‘ich bog‘lanish A/1, B/2, C/3, D/4, E/5. Har bir harf raqamlari alohida yuritiladi. Sozlama yangi cheklarga ta’sir qiladi; avvalgi cheklar o‘z harfi va operatorida qoladi. Demo hisoblar: `manager`, `manager2`, `manager3`, `manager4`, `manager5`. Ishchi hisoblarni Foydalanuvchilar sahifasida yarating.


## Logotiplar va belgilar

Tizim sozlamalaridagi **Logotiplar va interfeys belgilari**dan joyini tanlang, PNG/JPEG yuklang va saqlang. Tizim hamda kiosk logotiplari alohida. Standartga qaytarish faqat tanlangan belgini tiklaydi. Beshta bo‘lim rasmlari **Bo‘lim logotipi** shaklida boshqariladi. Kiosk bosh ekranida yangilanish 10 soniya ichida ko‘rinadi; kabinetni qayta ochganda saqlangan rasmlar yuklanadi.

## Talabalarni o‘zgartirmasdan Excel’dan qo‘shish

Telefon murojaati va murojaat kartasida talabani ism-familiyasi, uning bir qismi yoki HEMIS ID bilan qidiring. `Qidirish` tugmasi yoki Enter natijalarni ochadi. Ro‘yxatdan kerakli talabani tanlang, keyin murojaatni saqlang. Aniq HEMIS ID topilsa, talaba kartasi darhol ochiladi. Natijalar 20 tadan ko‘p bo‘lsa, qidiruvni aniqlashtiring. Qidirish talabalar bazasini o‘zgartirmaydi.

Talabalar bazasidagi Excel shaklidan asl faylni tanlang. HEMIS ID bo‘yicha mavjud yozuv o‘zgartirilmaydi. Ism va barcha yettita asl ustun qiymatlari saqlanadi. Takroriy ID yoki noto‘g‘ri qator bo‘lsa butun import bekor qilinadi. Faylda bo‘lmagan guruh va yo‘nalish taxmin qilinmaydi. Yangi Excel yozuvlari dastlab «Faol» holatida yaratiladi; bu universitetdagi o‘qish holatini tashqi tizimdan tekshirish natijasi emas. Ishchi bazaning zaxirasini saqlang.


## Birinchi admin paroli mos kelmasa

START-WINDOWS.bat endi fayl mavjudligiga emas, bazadagi hisoblar mavjudligiga qaraydi. Bo‘sh baza avvalgi muvaffaqiyatsiz urinishdan qolgan bo‘lsa ham login/parol yaratish takrorlanadi. Parollar mos kelmasa shu oynada qayta kiritiladi. Mavjud hisob/parol o‘zgartirilmaydi. Eski nusxada serverni Ctrl+C bilan to‘xtatib, loyiha papkasida `py -3 navbot\app.py --db navbot\navbot.sqlite3 --init-admin` buyrug‘i bilan birinchi adminni yarating; keyin START-WINDOWS.bat ni oching. Bazani o‘chirmang.

Excel hisobotining yuqorisida universitetning to‘liq nomi, alohida ofis/hisobot sarlavhasi va davr ko‘rsatiladi. To‘q ko‘k fonda 28 punktli universitet nomi, och kulrang-ko‘k ustun sarlavhalari va aniq katak chegaralari qo‘llanadi. Yashil fon olib tashlangan; Excelning bo‘sh katak chiziqlari ham ko‘rinadi. H ustuni — mas’ul menejer; I–K — ko‘rilgan chora; L — murojaat qilish usuli.

## Til va ko‘rinish menyulari

Yuqorida joriy til yozilgan bitta ochiladigan tugma bor. Uni bosib o‘zbekcha,
ruscha yoki inglizchani tanlang. Yonidagi bitta quyosh/oy tugmasini har bosganda yorug‘ va
to‘q ko‘rinish almashadi; bu tugma menyu ochmaydi. Tanlov keyingi kirishda ham saqlanadi. Escape yoki
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

## Profil rasmi va logotipni o‘chirish

Har bir xodim `Mening profilim` bo‘limida PNG/JPEG (2 MBgacha) rasm tanlab, `Rasmni saqlash` orqali o‘z profil rasmini yangilaydi. Rasm profil kartasi va yuqoridagi hisob tugmasida ko‘rinadi. `Rasmni o‘chirish` bosh harf ko‘rinishini qaytaradi. Boshqa xodim profil rasmini o‘zgartirish vakolati berilmaydi.

Administrator `Tizim sozlamalari → Bo‘lim logotipi` ichida bo‘limni tanlab, `Logotipni o‘chirish`ni bosadi. Faqat shu bo‘lim logotipi o‘chadi va kioskda standart belgi qaytadi.

## Boshlang‘ich Dashboard

Tizimga kirganda Dashboard ochiladi (vaqtinchalik parolni almashtirish talabi bundan oldin turadi). Superadmin va direktor barcha murojaatlarni, boshqa xodimlar esa o‘z vakolatlari doirasidagi murojaatlarni ko‘radi. Jami, faol (yopilmagan), yakunlangan va muddati o‘tgan murojaatlar; Toshkent sanasi bo‘yicha bugungi son va oxirgi 7 kun dinamikasi; holatlar, kanallar va so‘nggi beshta murojaat ko‘rsatiladi. Raqamlar mavjud murojaatlar ro‘yxatidan olinadi; o‘chirilgan yozuvlar kiritilmaydi. Yangilanish avtomatik. Murojaat qatorini bosish kartasini ochadi. Hisobot va yangi murojaat tugmalari tegishli vakolatlarda chiqadi.

Excel hisobotida «Qabul qilgan xodim F.I.Sh.» murojaatni qabul qilgan menejerni ko‘rsatadi. Xodim murojaatni o‘zida qoldirsa yoki o‘zi hal qilsa, muddat qo‘yilgan bo‘lsa ham «Yo‘naltirildi (muddat)» katagi bo‘sh qoladi. Boshqa xodimga biriktirilganda shu katakda uning ism-familiyasi va belgilangan muddat chiqadi.

Murojaatlar va arxiv oynalarida takroriy katta kabinet sarlavhasi olib tashlangan: ro‘yxat va karta yuqorida boshlanadi. Superadminning «Murojaat va navbatlarni tozalash» tugmasi murojaatlar ro‘yxati sarlavhasi yonidagi «⋯» menyusida joylashgan. Tasdiqlash va parol bilan tekshirish talablari saqlanadi.

## Xodimlarni tahrirlash, faol/nofaol qilish va o‘chirish

Superadmin «Xodimlar va loginlar → Xodimlar ro‘yxati»da har bir hisobning ism-familiyasi, login, rol, bo‘lim va operator raqamini tahrirlaydi. O‘zgartirishdan so‘ng xodimning eski sessiyalari yopiladi; parol saqlanadi. Yakunlanmagan murojaatlari bor xodimning rol, bo‘lim va oynasini almashtirish bloklanadi, ism va loginni tahrirlash mumkin.

«Nofaol qilish» kirishni darhol to‘xtatadi, eski sessiyalarni bekor qiladi va yangi yo‘naltirish ro‘yxatidan chiqaradi. Hisob ro‘yxatda qoladi va «Faollashtirish» bilan qayta ochiladi; nofaol hisobning operator raqami bandligicha qoladi. Oldingi ishlari superadmin nazoratida qoladi.

«O‘chirish»da hisob loginini kiritib tasdiqlash kerak. Yakunlanmagan murojaatlar bo‘lsa o‘chirish rad etiladi. Hisob ishlatiladigan ro‘yxatlardan chiqariladi, profil rasmi o‘chadi, operator raqami bo‘shaydi; tarixdagi xodim havolalari va murojaatlar saqlanadi. Eski login boshqa hisobga berilmaydi. O‘chirilgan hisobni faollashtirish mumkin emas — vaqtincha yopish uchun «Nofaol qilish»ni tanlang.

O‘z hisobini o‘chirish/nofaol qilish yoki o‘z rolini almashtirish mumkin emas. Oxirgi faol superadmin himoyalangan. Amallar auditga yoziladi.

## Bo‘lim xodimlari va alohida xodim raqami

Yangi xodim yaratish va tahrirlashda «Rol» ro‘yxatidan O‘quv bo‘limi, Xalqaro aloqalar bo‘limi, Xodimlar bo‘limi yoki Ma’lumotlar bazasi menejerini tanlash mumkin. Barchasi ichki `executor` vakolatidan foydalanadi: o‘ziga biriktirilgan ishlarni ko‘radi, qaytaradi yoki javobni tasdiqqa yuboradi. Administrator yoki menejer vakolati qo‘shilmaydi. Bo‘lim nomi tanlovga mos avtomatik qo‘yiladi; mavjud foydalanuvchilar avtomatik qayta taqsimlanmaydi.

«Operator raqami» faqat menejer uchun ko‘rinadi va majburiy. Ma’lumotlar bazasi menejeri uchun esa alohida, ixtiyoriy «Xodim raqami» bor: 1–20 ta raqam, masalan `007`. Bu navbat/oyna raqami emas va operatorni boshqarish huquqini bermaydi. Boshlang‘ich nollar saqlanadi; bir raqam ikki hisobga berilmaydi. Raqamni profil va xodimlar ro‘yxatida ko‘rish, tahrirlash mumkin.

## Talabalar filtrlari, sahifalar va bazani tozalash

Talabalar bazasida fakultet va ta’lim yo‘nalishini tanlang, ism/HEMIS ID/guruh bo‘yicha qidiring. Filtrlar birgalikda ishlaydi; har sahifada ko‘pi bilan 50 talaba chiqadi. Filtr yoki qidiruv o‘zgarsa birinchi sahifaga qaytiladi. Bo‘lim boshlig‘i va direktor faqat ko‘radi; o‘chirish superadminga tegishli.

Superadmin bitta qatorni, «Filtrdagi talabalarni o‘chirish» orqali barcha mos yozuvlarni yoki «Barcha talabalarni o‘chirish» orqali butun joriy ro‘yxatni tozalashi mumkin. «Filtrdagi» faqat ko‘rinayotgan 50 qatorni emas, barcha mos talabalarni qamraydi. Avval zaxira nusxa oling. Tasdiq oynasida sonni va superadmin parolini kiriting. Bekor qilish hech narsani o‘chirmaydi. Tayyorlangan ro‘yxat 15 daqiqa amal qiladi; shu paytdan keyin yangi qo‘shilgan talabalar unga qo‘shilmaydi. Talaba yozuvlari shu orada o‘zgarsa amal to‘liq rad etiladi.

Eski murojaatlarning talaba ma’lumotlari o‘chirishdan oldin murojaat ichida nusxa sifatida saqlanadi. Murojaatlar, tarix, xodimlar, navbatlar, audio va sozlamalar o‘chmaydi. Qayta yuklangan talaba yangi qidiruvlarda chiqadi; oldingi murojaatda saqlangan ma’lumot o‘zicha qoladi. Murojaatni tahrirlab talabani qayta bog‘lash yangi ma’lumotga o‘tkazadi. Talabaning murojaati ham o‘chirilsa, saqlangan nusxa ham tozalanadi.

## Talabaning faol/nofaol holati

Talabalar jadvalida fakultet va yo‘nalish alohida ustunlarda. Keng ekranda filtrlar, qidiruv va o‘chirish tugmalari bitta qatorda; kichik ekranlarda mos ravishda joylashadi. «Boshqarish» ustunida superadmin «Nofaol qilish», «Faollashtirish» yoki «O‘chirish»ni tanlaydi. Faol/nofaol qilish yozuvni o‘chirmaydi va bu bo‘limda ishlash vakolatlarini o‘zgartirmaydi. Qidiruvda nofaol talaba ham holati bilan ko‘rinadi.

Ushbu yangilanish birinchi marta o‘rnatilganda mavjud talabalar «Faol»ga o‘tkaziladi. Bu bir martalik amal: keyinchalik qo‘lda qo‘yilgan «Nofaol» holat qayta ishga tushganda saqlanadi. Excel orqali yangi qo‘shilgan talabalar «Faol»dan boshlanadi; mavjud HEMIS ID holati o‘zgartirilmaydi. JSON importida aniq berilgan holat saqlanadi. Holat amallari auditga yoziladi.

## Mutaxassislik shifri bilan 8 ustunli Excel

Quyidagi aniq ustunlar tartibi ham qabul qilinadi: `Talaba ID`, `To‘liq ismi`, `Kurs`, `Fakultet`, `Guruh`, `Mutaxassislik`, `Ta’lim turi`, `Ta’lim shakli`. «Mutaxassislik» 8 xonali shifr bo‘lishi kerak, boshlang‘ich nollar saqlanadi. Jadval, filtr va talaba kartasida u «Mutaxassislik shifri» nomida chiqadi; fakultet alohida qoladi. Faylda jins ustuni bo‘lmasa, jins taxmin qilinmaydi.

Yangi talabalar barcha asl 8 katak va manba nusxasi bilan saqlanadi. Mavjud ID uchun faqat bo‘sh mutaxassislik shifri va guruh to‘ldiriladi; mavjud ism, fakultet, kurs, holat va to‘ldirilgan qiymatlar almashtirilmaydi. Import natijasidagi «To‘ldirildi» shu yozuvlar sonidir. Oldingi 7 ustunli shakl ham qo‘llab-quvvatlanadi.

Qidiruv natijasidan tanlangan talaba kartasida faqat Excel shaklidagi ma’lumotlar ko‘rinadi: ism-familiya va ID, kurs, fakultet, guruh, mutaxassislik shifri, ta’lim turi va shakli. Telefon murojaati va mavjud murojaat kartasida bir xil ko‘rinish ishlatiladi. Jins va holat bu kartada chiqarilmaydi; bazadagi ma’lumotlar o‘zgartirilmaydi.

## Bir hisobda bir nechta rol va profil orqali almashish

Asosiy hisob roli saqlanadi. Superadmin «Mening profilim → Rolni almashtirish»da barcha rollar va bo‘limlar orasida o‘tadi. Bo‘lim boshlig‘i uchun superadmin xodimni yaratish/tahrirlashdagi «Ruxsat etilgan rollar»dan bir nechtasini belgilaydi. Bo‘lim boshlig‘i profilida faqat shu tanlovlar va asosiy bo‘lim boshlig‘i roli bor; superadmin roli hech qachon berilmaydi. Boshqa asosiy rollarga qo‘shimcha rollar berilmaydi.

Menejer vakolati berilgan bo‘lim boshlig‘iga superadmin band bo‘lmagan 1–30 operator raqamini belgilashi kerak. Superadmin birinchi marta menejer roliga o‘tayotganda profilidan o‘ziga bo‘sh operator raqamini tanlaydi. Boshqa xodimga tegishli raqamni olish mumkin emas. Alohida xodim raqami operator raqami o‘rnida ishlatilmaydi.

Rol almashganda tanlangan menyu va server vakolatlari ishlaydi, hisob egasining IDsi va rasmi saqlanadi; boshqa xodim akkauntiga kirilmaydi. Ijrochi bo‘limi tanlansa shu bo‘lim konteksti qo‘llanadi, bo‘lim boshlig‘i roliga qaytilganda asosiy bo‘lim tiklanadi. Faol rol joriy sessiyaga tegishli; yangidan login qilganda asosiy rol ochiladi. Eski sessiya kaliti almashadi, auditga yoziladi. Ruxsatlar o‘zgartirilganda xodimning barcha eski sessiyalari bekor qilinadi. Asosiy rolni o‘zi tahrirlash taqiqi saqlanadi; profil orqali faqat ruxsat etilgan faol rol almashtiriladi.

## Kengaytirilgan audit va xavfsizlik ogohlantirishlari

Superadmin «Audit jurnali»da sana oralig‘i, xodim/login, IP, amal, natija, hodisa turi va xavf bo‘yicha filtrlaydi. Har sahifada50 yozuv. Alohida ustunlarda IP, HTTP usuli/manzili, natija, xavf, fayl nomi va hajm, takrorlar soni chiqadi. Eski yozuvlarda avval qayd etilmagan IPni tiklab bo‘lmaydi; yangi yozuvlardan boshlab saqlanadi.

10 daqiqada bir IPdan10 ta muvaffaqiyatsiz kirish yoki5 daqiqada3 ta maxfiy manzilni qidirish urinishida15 daqiqalik blok qo‘yiladi. Blok va yangi login IP haqidagi xabar superadminning bildirishnomasi va ochiq sahifadagi bannerda chiqadi. Auditdagi «Blokdan chiqarish» tekshirilgan IPni qayta ochadi. Bir IPni bir nechta xodim ishlatishi mumkinligini hisobga oling.

«Brauzer xabarlari» HTTPS va brauzer ruxsatini talab qiladi. Hozirgi lokal HTTPda tizim ichidagi xabar ishlaydi. Brauzer yopiq paytdagi fon Web Push hali ulanmagan. Qoidalar barcha hujumni aniqlash kafolati emas; Nginx, UFW va SSH qatlamlari o‘z jurnallarini yuritadi. Tafsilotlar: [Audit himoyasi](../deploy/AUDIT-SECURITY.md).

Talabalar Telegram boti: talaba kartasida “Telegramga bog‘lash”ni bosing. Shaxsini tekshirib, 10 daqiqalik bir martalik kod yarating. Talaba botda `/start`, HEMIS ID va kodni kiritadi. Rahbar tasdiqlagan javob va faqat tanlangan fayllar avtomatik yuboriladi. Batafsil foydalanish, o‘rnatish va yuborish xatolari: [TELEGRAM-BOT.md](TELEGRAM-BOT.md).
