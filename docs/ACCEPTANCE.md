# v0.5 lokal sinov dalillari — 2026-11-17

Bu hujjat butun texnik talab yakunlanganini anglatmaydi. Quyidagi lokal funksiyalar bajarildi; tashqi xizmatlar va qolgan modullar alohida ko‘rsatilgan.

| Talab | Bajarilgan va tekshirilgan |
| --- | --- |
| 2–3: kiosk, chek, mazmun | 5×5 katalog, uch til, serverda takror kalitga bitta chek/ariza, chop etish/qayta chop etish, xizmat nomining nusxasi, vaqt |
| 4.1: HEMIS ID | Lokal SQLite/fayl importi, raqamli va H-prefiksli ID, F.I.Sh./yo‘nalish/kurs/ta’lim shakli, arizaga biriktirish |
| 4.2–4.4: ijro | Menejerda saqlash/joyida hal qilish, mas’ulga topshirish, sabab bilan qaytarish, amaldagi muddatni saqlab qayta topshirish, javob/tasdiq/tuzatish/yopish |
| 5: muddat | UTC saqlash, Toşkentda ko‘rsatish, qayta ochilganda hisoblash, sariq chegara, kechikish, rahbar muddat o‘zgartirish tarixi. Huquqiy qoidalar tasdiqlanmagan |
| 6: EDO | Yangi/biriktirilgan/yuborilgan/qaytarilgan/yaqin/o‘tgan/tasdiq/arxiv filtrlari, talaba/izoh/javob/tarix |
| 7: hisobot | Saqlangan reyestr, sana/bo‘lim/menejer/xizmat bo‘limi/kanal/holat filtrlari, kunlar dinamikasi, bo‘limlar kesimi, XLSX/CSV, arxiv |
| 8: Superadmin | Xodim yaratish, vaqtinchalik parol, mavjud rollar; katalog/tarjima/TV/ovoz parametrlarini saqlash. Cheklanmagan rol/shablon konstruktorlari hali yo‘q |
| 10: talabalar | JSON fayldan atomar import va HEMIS ID bo‘yicha yangilash, offline lokal qidiruv; admin sozlaydigan LMS sinxronlash (mos JSON formatida) |
| 11–13: TV/tablo/tillar | Chap chaqiruv, o‘ng xizmat, past kutish; qabulda qo‘shish/yakunida chiqarish; 3 miltillash; tanlangan chek/ovoz tili; TV tili alohida |
| 14: shaxsiy kabinet | Login, xeshlangan parol, sessiya, joriy parol bilan yangilash, resetda vaqtinchalik parol va sessiyalarni bekor qilish |
| 15: sozlamalar | Uch tilda nomlar/chek pastki matni/ovoz/TV sarlavhalari, oldindan ko‘rish, PNG/JPEG logo yuklash va kioskda yangilash |
| 18: saqlash | Eski baza migratsiyasi va qayta tiklanadigan migratsiyadan oldingi nusxa; yo‘riqnomada yangilash/qaytish tartibi |

## Bajarilgan tekshiruvlar

- `python3 -m unittest discover -s tests -p 'test_*.py' -v`: 52 ta muvaffaqiyatli test.
- `node tests/workflow-browser.cjs`: bo‘sh vaqtinchalik bazada to‘liq Chromium UI zanjiri; sahifa JS xatolari yo‘q.
- `node tests/queue-browser.cjs`: 3/3 til, chek/vaqt/qayta chop etish, chaqirish/qayta chaqirish/miltillash/qabul/yakunlash, TV/tablo, TV joylashuvi va shaxsiy ma’lumot ko‘rinmasligi.
- `node tests/student-browser.cjs`: login bilan topish/topilmaslik/noto‘g‘ri ID, maydonni pollingda saqlash.
- Admin sozlamasi, chek oldindan ko‘rish va PNG logoni kioskda ko‘rsatish haqiqiy Chromium oynasida tekshirildi.
- CP1251 standarti takrorlangan testda UTF-8 katalog to‘g‘ri ochiladi. Windowsning o‘zida ushbu versiya hali ishga tushirilmagan.

## Qolgan ishlar va qabul cheklovlari

- Telegramga tasdiqlangan talaba akkauntini bog‘lash, javob/baho 1–5, yuborilmagan xabarlar navbati: bot va identifikatsiya shartnomasi bilan keyingi bosqich. Hozir panel ichida davriy olinadigan xabarlar bor; bu haqiqiy Telegram/OS push emas.
- LMSdan ariza/talaba/holat/javob/baho almashish, tashqi ID deduplikatsiyasi va qo‘lda sinxronizatsiya: API manzili, maydonlari va ruxsatlari kerak. Ulangan deb ko‘rsatilmaydi.
- Katalogni 5×5 dan cheklanmagan yaratish/tartiblash, ixtiyoriy rollar va vakolat matritsasi, bo‘lim boshlig‘ining delegatsiyasi, dinamik ariza shablonlari va fayl ilovalari versiyasi hali bajarilmagan. Yakuniy 19-bo‘lim matritsalari ham berilishi kerak.
- Xodim kabinetlariga uch til va yorug‘/to‘q mavzu qo‘shilgan. Shaxsiy matnlar va ismlar tarjima qilinmaydi. TV interfeys tili alohida sozlanadi.
- Haqiqiy 80mm printer, ovozning eshitilishi, uzbekcha tizim ovozi, Info KeyOS/LED protokoli, boot/kiosk rejimi, printer xatosini qurilmadan olish tekshirilmagan. Oddiy brauzer print dialogi ishlatiladi; maxsus Windows kiosk launcher dialogsiz tasdiqlash uchun qo‘shilgan.
- LAN/WAN, HTTPS, ishchi server/subdomen, zaxiradan real operatsion qaytish, tarmoq uzilishi/tiklanishi, qurilma dasturini yangilash — haqiqiy infratuzilmada qabul qilinadi. Ubuntu yo‘riqnomasi tayyor, lekin serverga o‘rnatilmadi.

## Ko‘rinishlar

Bular sun’iy ma’lumotli ishlayotgan ilovadan olingan; dizayn maketi emas.

- [Kiosk](previews/kiosk.png)
- [TV](previews/tv.png)
- [Menejer](previews/manager.png)

Avtomatik print yangilanishi: xizmat bosilganda brauzer print chaqiruvi avtomatik bir marta bajariladi; qayta chop etish ayni chekni ishlatadi. START-KIOSK-WINDOWS.bat alohida Google Chrome profilini --kiosk-printing bilan ochadi. Haqiqiy Windows dialogsiz chop etish va printer holati hali qurilmada tekshirilishi kerak.

TV yangilanishi: ovozni yoqish tugmasi olib tashlandi. Chaqiruv ovozi avtomatik; maxsus Windows TV launcheri autoplay siyosatini belgilaydi. Uch tilli Speech API chaqiruvlari va tugma yo‘qligi brauzer sinovida tekshiriladi; fizik ovoz Windowsda tasdiqlanishi kerak.

## Oxirgi qabul: admin qo‘lda sozlamalari, enli kiosk, Excel va fayllar

Admin integratsiya shakllari (saqlash, sirni qayta bermaslik, ulanish sinovi, mos formatdagi talabalar sinxronlash), audio yuklash/usul/sinov/TV ketma-ket ijrosi, til/mavzu va ochiq shakl matnini saqlash `tests/enhancements-browser.cjs` orqali tekshirildi.1024×768 va1280×1024 ekranlarda kiosk3+2 bo‘limni scrollsiz chiqaradi. Excel sarlavhalari,12ustun, vaqt zonasi, xavfsiz matnlar va vakolat filtrlari XMLtest hamda mustaqil openpyxl o‘qishi bilan tekshirildi. openpyxl faqat tekshiruv vositasi, ilovaga tashqi paket kerak emas.

Fayl yuklash/yuklab olish vakolatlari, buzilgan fayllarni rad etish, takroriy yuklashni bitta saqlash va arxivda saqlash server testlarida tekshirildi. Ijrochi javobiga fayl qo‘shib rahbarga yuborish, rahbar tasdiq fayli qo‘shishi va arxivda ikkala fayl qolishi to‘liq brauzer zanjirida tekshirildi.

Haqiqiy universitet API/tokenlari kiritilmagani uchun real HEMIS/LMS/Telegram ulanishiga muvaffaqiyat da’vo qilinmaydi. Tashqi so‘rovlar bloklarining testlari soxta transport chegarasidan foydalanadi; brauzer testida tashqi tarmoqqa xabar yuborilmagan. Windows, real karnay/printer va Info KeyOS apparat sinovi hali kerak. Batafsil: [admin qo‘llanmasi](ADMIN-QOLLANMA.md).

## Bo‘lim harflari va ommaviy audio

- `python3 -m unittest discover -s tests -p 'test_*.py'`: 57 test o‘tdi; beshta marshrut, mustaqil hisoblagichlar, mavjud chekni saqlash, noto‘g‘ri operatorni rad etish, 500 raqam yozuvi va asl to‘rtta fayl tartibi tekshirildi.
- `node tests/routing-audio-browser.cjs`: admin sozlamasi, namunani o‘rnatish, interfeysdan 500 raqam + 4 qo‘shimcha harf + 4 operator yozuvini yuklash, beshta menejer inboxi, TV/tablo va ketma-ket 20 audio qismi o‘tdi.
- `node tests/workflow-browser.cjs` va `node tests/enhancements-browser.cjs`: mavjud jarayonlar regressiyasi o‘tdi; sahifa JavaScript xatosi yo‘q.
- Audio test ijro chegarasini almashtiradi; haqiqiy karnay va Windows qurilmasidagi tovush alohida tekshiriladi.


## Logotiplar, ikonalar va asl talabalar importi

- `node tests/branding-browser.cjs`: tizim/kiosk logotiplari, menyu/xizmat/mavzu ikonkalari, saqlanishi va standartga qaytarish o‘tdi. Kiosk yo‘riqnoma qatori va demo login banneri yo‘q. Sahifa xatosi yo‘q.
- `python3 -m unittest discover -s tests -p 'test_*.py'`: 86 test; rasm ruxsatlari, yaroqsiz fayllar, almashtirilgan rasmni tozalash, XLSX faqat yangi yozuvni qo‘shishi, takroriy ID va ruxsat tekshirildi.
- Workflow, enhancements va routing/audio brauzer regressiyalari o‘tdi.
- Foydalanuvchi fayli 6262 ta noyob ID va 7 ustundan iborat. 43834 ta asl katak qiymati ishchi bazada mustaqil openpyxl o‘qishi bilan solishtirildi. Xususiy fayl/baza repozitoriyga qo‘shilmagan. Asl fayl SHA-256 va import hisoboti xususiy papkada saqlangan.


## SSH terminalida test izolyatsiyasi

Birinchi admin CLI testi controlling TTY mavjud bo‘lganda fixture stdin o‘rniga
operator terminalidan getpass kutishi qayta hosil qilindi (10s TimeoutExpired).
POSIX test subprocesslari yangi sessiyaga ajratildi; haqiqiy admin yaratish va
ishchi hisoblar o‘zgartirilmadi. `script -q -e -c "python3 -m unittest discover
-s tests -p 'test_*.py'" /tmp/navbot-tests.log` bilan haqiqiy PTY ichida94 test
41.923 soniyada o‘tdi, interaktiv parol so‘rovi bo‘lmadi.


## Ikkita ixcham menyu va boshqariladigan tozalash

102 ta unit/HTTP testi PTY ichida o‘tdi. Yangi tekshiruvlar admin/parol talabi,
versiyalar mosligi va atomik bekor qilish, barcha umumiy bazalar saqlanishi,
ilova yuklab olishning bekor qilinishi, eski so‘rovlar va restart orqali qayta
yaratishning rad etilishini qamraydi. Brauzerda til/mavzu menyulari, bitta
murojaatni o‘chirish, noto‘g‘ri parolni rad etish, keyin kelgan yangi yozuvni
saqlab snapshot bo‘yicha tozalash, raqamlarni takrorlamaslik o‘tdi. Workflow,
enhancements, CSP, branding va500-audio/five-operator regressiyalari o‘tdi.
Haqiqiy serverdagi tozalash deployment paytida avtomatik bajarilmaydi;
superadmin ko‘rsatilgan raqamlar va sonni ko‘rib, o‘z paroli bilan ishga tushiradi.

Info kiosk ekrani: bo‘lim/xizmat tugmalari bo‘sh pastki joyni to‘ldiradi (3+2, 1024×768, 1280×1024 va 1920×1080). Tugmalardagi oldinga strelkalar olib tashlandi; xizmatlarda ham joriy bo‘lim logosi saqlanadi. `tests/kiosk-display-browser.cjs` o‘lchamlar, strelkasiz kartalar, bo‘lim logosi, bitta avtomatik print, yangi sahifasiz chek, print CSS, qayta yuklashda takrorlanmaslikni tekshiradi. `START-KIOSK-LAN-WINDOWS.bat` mavjud LAN serveriga alohida Chrome profili bilan ulanadi; lokal server/baza yaratmaydi. Fizik Windows printerida ishlashi hali amaliy tekshirilishi kerak.

Ixcham chek: xizmat tanlangach, qog‘oz maketi ekranda ochilmaydi; bosh menyu ko‘rinib turadi, navbat raqami oynasi va qayta chop etish/yangi navbat tugmalari umuman yaratilmaydi. Print avtomatik bir marta chaqiriladi. `window.print()` qaytishi bilan menyu darhol qayta faollashadi; `afterprint` hodisasini kutish yoki taymer yo‘q. Yashirin chek maketi print uchun saqlanadi, ekranda ko‘rsatilmaydi. Reload saqlangan chekni avtomatik qayta chiqarmaydi. Bu printerdan qog‘oz muvaffaqiyatli chiqqanini tasdiqlamaydi. Chek 74 mm kontent kengligida, kichik matnlar, 40 px navbat raqami va minimal qator oralig‘i bilan chiqadi. Qog‘oz o‘lchami/uzluksiz lenta va kesish uzunligi Windows printer drayverida boshqariladi. Print maketi ekran uchun yashiriladi, shaxsiy ma’lumot/yozuvlar va navbat raqami o‘zgarmaydi.

Ixcham kiosk dizayni (keyingi talab): kartalar ekranning bo‘yiga cho‘zilmaydi. Bir xil kenglik/balandlikdagi oq kartalar, yashil belgi va xizmat kartasida yupqa yashil chiziq; desktopda 3+2 markazlashgan tartib. Tegish maydoni 150–220 px, ekran bo‘ylab kengligi moslashadi; kichik ekranlarda moslashuvchan. Bu avvalgi “pastki bo‘sh joyni to‘liq to‘ldirish” ko‘rinishining o‘rnini oladi. To‘liq ekran Chrome launcher orqali saqlanadi.

Chrome preview miltillashini yo‘qotish: `window.print` yo‘li Chrome ichki oynasini qisqa ko‘rsatishi mumkin, hatto `--kiosk-printing` bo‘lsa ham. Sayt CSSi bu oynani boshqarmaydi. Yangi Windows yordamchisi rejimida `window.print` umuman chaqirilmaydi: server navbati → yordamchi → .NET StandardPrintController → standart Windows printeri. Rejim superadminning Kiosk, TV va tablo bo‘limida sozlanadi; sozlama JSONi yordamchi ZIP papkasiga qo‘yiladi. Avvalgi BATning o‘zi native rejimni yoqmaydi. Standart holat brauzer rejimi; foydalanuvchi aniq sozlamaguncha ishlash tartibi avtomatik almashmaydi.

`test_kiosk_printer.py` haqiqiy HTTP bilan vakolat, offline/virtual printer holati, eski klientdan himoya, idempotent navbat, claim/ack, uzilish/noaniq holat, qayta yuborish tasdig‘i va sirlar auditga chiqmasligini tekshiradi. `kiosk-native-browser.cjs` Windows yordamchisi javobini test klienti bilan almashtirib, real API jarayonida Chrome print chaqirilmaganini, popup yo‘qligini, bosh menyuni va adminning konfiguratsiya yuklashini tekshiradi. Bu Windows PowerShell/.NET drayveri fizik qurilmada ishlaganini tasdiqlamaydi; Linux muhitida Windows yoki printer mavjud emas. Kioskdagi birinchi real sinov alohida bajariladi. Kartalar shu ko‘rinishda kattalashtirildi: desktopda 180–280 px.
