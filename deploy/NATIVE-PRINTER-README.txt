NAVBOT: Chrome oynasisiz bevosita Windows printeriga chek chiqarish

1. ZIPni alohida papkaga oching, masalan C:\NAVBOT-Printer.
2. Avval faqat kompilyatsiyani, chop etmasdan tekshirish:
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\NAVBOT-PRINT-AGENT.ps1 -ValidateOnly
   Compilation: OK chiqishi kerak. Bu rejim chop etmaydi va serverga ulanmaydi.
   80 mm fizik chek printeri Windows DEFAULT printeri bo'lsin.
   PDF/XPS/OneNote/Fax virtual printerlari qabul qilinmaydi.
   Windows test sahifasi oldin normal chiqishi kerak.
3. NAVBOT superadmin: Kiosk, TV va tablo -> Oynasiz chek chiqarish.
   Printer sozlamasini yaratish tugmasini bosing.
   printer-config.json yuklanadi. Uni shu papkaga qo'ying.
   Bu fayl maxfiy. Telegram/chat/GitHubga yubormang.
4. Eski kiosk oynalarini Alt+F4 bilan yoping.
5. START-NAVBOT-NATIVE.bat faylini bosing. Windows PowerShell yordamchisi
   yashirin ishlaydi va alohida Chrome profilida to'liq ekran ochiladi.
6. Superadmin sahifasida Yordamchi ulangan holati chiqishini kuting.
7. Xizmat bosilganda Chrome print oynasi chaqirilmaydi. Yordamchi serverdan
   ishni olib, standart Windows drayveri bilan chop etishga yuboradi.
   Sayt faqat bosh menyuni ko'rsatadi.

Diqqat: sozlama yaratilganda yordamchi rejimi yoqiladi. Ulanmaguncha
kiosk yangi chek yaratmaydi; yashirincha Chrome usuliga o'tilmaydi.
Bir server uchun bitta kiosk printeri qo'llanadi.

HOLATLAR:
- Windows navbatiga yuborildi: spooler qabul qildi; qog'oz chiqqani tasdiqi emas.
- Natija noma'lum: yordamchi to'xtagan yoki javob yo'qolgan. Avtomatik qayta
  chop qilinmaydi. Superadmin oldingi chekni tekshirib, qayta yuboradi yoki
  bekor qiladi. Qayta yuborishda takroriy chek chiqishi mumkin.
- Yordamchi ishlamasa, yangi chek yaratilmaydi. Tarmoq/default printerni tekshiring.

Yordamchini tekshirish:
PowerShell oynasida shu papkadan bajaring:
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\NAVBOT-PRINT-AGENT.ps1
Maxfiy kalitlar yoki xabar matnlari konsolga yozilmaydi.
Jurnal: %LOCALAPPDATA%\NavBoT\PrinterAgent\print-journal.json
Uni o'chirmang: qayta chop etishdan himoya uchun kerak.
Yordamchi ikki marta bosilsa, ikkinchi jarayon printerga ulanmaydi.

To'xtatish: kiosk Chrome oynasini Alt+F4 bilan yoping. Yordamchi alohida
PowerShell jarayoni bo'lib ishlaydi; uni Task Managerdan to'xtatish mumkin.
Tugallanmagan ish bor paytda o'chirish natijani noma'lum holatiga olib kelishi mumkin.
Qayta ishga tushirish: START-NAVBOT-NATIVE.bat.

Bu paket Windows PowerShell 5.1 va o'rnatilgan printer drayveridan foydalanadi.
Python, yangi port, lokal HTTP server yoki brauzer kengaytmasi kerak emas.
HTTP LAN manzilida token tarmoq orqali shifrlanmaydi; mavjud ishonchli LAN
uchun. Ochiq tarmoqda ishonchli sertifikatli HTTPS manzilidan foydalaning.
Haqiqiy Windows qurilmasi va printerda birinchi sinov alohida bajariladi.


TEZROQ AVTOMATIK ISHGA TUSHIRISH (Windows foydalanuvchisiga kirishda):
- Yangi ZIPdagi barcha fayllarni printer-config.json bor papkaga oching.
- TEST-NAVBOT-WINDOWS.bat faqat sintaksis/kompilyatsiyani tekshiradi;
  printerga chiqarmaydi, Windows sozlamalari yoki vazifalarini o'zgartirmaydi.
- INSTALL-NAVBOT-AUTOSTART.bat ni shu kiosk foydalanuvchisi ostida bir marta bosing.
- Dastur fayllar va kalitni %LOCALAPPDATA%\NavBoT\NativeKiosk ga nusxalaydi.
  Downloads papkasini ko'chirish/o'chirish bundan keyin avtoyuklashga ta'sir qilmaydi.
- Task Schedulerga joriy foydalanuvchi kirishi bilan ishlaydigan PT0S vazifa
  qo'shiladi. shell:startup papkasining Windows kechikishini kutmaydi.
- Eski NAVBOT Startup BAT/yorliqlari va printer-config.json avtomatik
  old-startup zaxira papkasiga ko'chiriladi; unrelated dasturlar tegilmaydi.
- Faqat joriy foydalanuvchining RestartApps sozlamasi o'chiriladi: Windows
  avvalgi VS Code/JSON oynasini qayta tiklamasin. Oldingi qiymat saqlanadi.
- Windows paroli, avtomatik login yoki Explorer shell o'zgartirilmaydi.
  Kiosk Windows foydalanuvchisiga kirilgandan keyin ochiladi, elektr yoqilgan
  zahoti yoki Windowsning o'zi yuklanishidan oldin emas.
- Windowsning o'z yuklanish va Chrome ochilish vaqti baribir kerak bo'ladi.
- Chrome ochilishi printer yordamchisini yoki avvalgi 3 soniyalik taymerni
  kutmaydi. Avval NAVBOT kutish ekrani ochiladi. Server/tarmoq tayyor bo'lgach,
  shu oynaning o'zida kioskka o'tadi. Konfiguratsiya JSONi brauzerga berilmaydi.
- Installer xato bersa, REMOVE-NAVBOT-AUTOSTART.bat qisman qo'llangan sozlamalarni
  ham saqlangan manifest orqali tiklaydi. Ruxsat yo'q bo'lsa, shu kiosk
  foydalanuvchisining Task Scheduler ruxsatini administrator tekshiradi.
- Bekor qilish: REMOVE-NAVBOT-AUTOSTART.bat. Faqat shu foydalanuvchining NAVBOT
  vazifasi olib tashlanadi; zaxiralangan yorliqlar va RestartApps avvalgi qiymati
  (keyin qo'lda o'zgartirilmagan bo'lsa) tiklanadi. Printer kaliti o'chirilmaydi.
- O'rnatilgan yo'l: %LOCALAPPDATA%\NavBoT\NativeKiosk.
  startup-status.txt bo'lsa, unda kalitsiz umumiy xato saqlanadi.
- Windowsdagi real logon/Task Scheduler va file:// navigatsiya shu qurilmada
  tekshirilishi kerak. Brauzer siyosati lokal HTMLni taqiqlagan bo'lsa,
  qurilma administratori aynan NAVBOT sahifasiga ruxsatni tekshiradi.
