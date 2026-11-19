# Talabalar Telegram boti

Bot mavjud NAVBOT bilan bir bazadan foydalanadi. Yangi murojaat kioskda yoki xodim orqali telefon qabulida yaratiladi. Botga yangi murojaat kiritish hozircha qo‘shilmagan.

## Talaba uchun

1. Botni ochib `/start` bosing va HEMIS ID kiriting.
2. Shaxsini tasdiqlagan xodimdan bir martalik kod oling. Telefon raqami bazada yo‘qligi sababli, HEMIS ID va Telegram kontaktining o‘zi shaxsni tasdiqlamaydi. Telefon orqali kod berishdan oldin tashkilot tasdiqlagan shaxsni tekshirish tartibidan foydalaning.
3. 8 belgili kodni 10 daqiqa ichida kiriting. Kod bir marta ishlaydi. 5 xato urinishdan keyin 15 daqiqalik cheklov qo‘yiladi. Qayta boshlash: `/start`.
4. Menyular: **Murojaatlarim**, **Jarayonni kuzatish**, **Profilim**, **Yordam**, **Til**. O‘zbek, rus va ingliz tillari mavjud. Jarayonni kuzatish asosiy menyuda alohida tugma.
5. Murojaatlar 5 tadan sahifalanadi; talaba faqat o‘z HEMIS IDiga biriktirilgan murojaatlarni ko‘radi. Profil faqat kelishilgan talaba jadvali ustunlarini ko‘rsatadi.

Telegram oynasi va tugmalarining rangini Telegram ilovasi mavzusi belgilaydi. Menyular tartibi, matnlar va NAVBOT nomi saqlanadi. Bot faqat shaxsiy chatda ishlaydi.

## Xodim uchun

- Superadmin yoki menejer talaba kartasidagi **Telegramga bog‘lash** orqali, shaxsini tekshirganini belgilab kod yaratadi. Kod faqat javobda bir marta ko‘rsatiladi; bazada uning xeshi saqlanadi. Yangi kod eskisini bekor qiladi.
- Bitta talaba bitta Telegram hisobiga, bitta Telegram hisobi bitta talabaga bog‘lanadi. Qayta bog‘lash uchun superadmin sabab bilan eski bog‘lanishni uzadi. Eski hisobga navbatdagi xabarlar bekor qilinadi. Yangi hisob ham xodim kodi bilan tasdiqlanadi.
- Ijrochi javob tayyorlab tasdiqqa yuboradi; bo‘lim boshlig‘i yoki superadmin tasdiqlaydi. Shunda javob avtomatik yuborish navbatiga tushadi. Talaba hali bog‘lanmagan bo‘lsa, tasdiqlangan javob bog‘langach yuboriladi.
- **Tasdiqlash** oynasida talabaga jo‘natiladigan fayllarni alohida tanlang. Odatiy holatda hech bir fayl tanlanmagan. Yangi yuklangan fayllarni yuborish ham alohida belgilanishi kerak. Ichki fayllar, izohlar, huquqiy asoslar, xodimlar tarixi va hali tasdiqlanmagan javob botga chiqarilmaydi.
- **Joyida hal qilish** rahbar tasdig‘i hisoblanmaydi; bunday javob avtomatik Telegramga yuborilmaydi. Telegram orqali javob berish uchun odatdagi ijrochi → rahbar tasdiqlash jarayonidan foydalaning. Avval yopilgan eski arizalarga bot o‘zidan tasdiq qo‘ymaydi.
- Murojaat kartasidagi Telegram bo‘limida navbat, yuborildi, yuborilmadi yoki yetkazilishi noma’lum holati chiqadi. “Yuborildi” — Telegram API xabarni qabul qilganini bildiradi; talaba o‘qiganini bildirmaydi.
- Telegram `429` javob bersa, ko‘rsatilgan muddatdan keyin qayta uriniladi. Bot bloklangan bo‘lsa yuborish to‘xtaydi. Tarmoq uzilib, natija noma’lum qolsa yoki xizmat yuborish paytida to‘xtasa, avtomatik takroriy xabar yuborilmaydi. Vakolatli xodim ogohlantirishni o‘qib **Qayta yuborish**ni bosadi; bunda dublikat borishi mumkin.
- Talaba yoki murojaat o‘chirilganda tegishli bot navbati va javob nusxalari tozalanadi. Nofaol talaba ma’lumotlari yuborilmaydi. Oldin Telegramga yetib borgan xabarlar yoki fayllarni bazadan o‘chirish Telegramdan ham o‘chirmaydi. Allaqachon tarmoqqa uzatilayotgan xabar bekor qilish bilan bir paytga to‘g‘ri kelsa, yetib borishi mumkin.

## Serverga o‘rnatish (nashrdan keyin)

Bot tokenini BotFather orqali oling va **Integratsiyalar → Telegram**da saqlang, **Faollashtirish**ni belgilang. Tokenni chatga, Gitga, buyruqlar tarixiga yoki xizmat fayliga yozmang. Avval “Ulanishni tekshirish” bilan botni tekshiring. Shu bot bilan boshqa polling dasturi yoki webhook bir vaqtda ishlamasligi kerak.

Quyidagi buyruqlar Ubuntu serverida, loyiha `/opt/navbot` va baza `/var/lib/navbot/navbot.sqlite3` bo‘lganda bajariladi. Avval yangilangan asosiy tizimni ishga tushiring, so‘ng worker o‘rnating:

```sh
sudo systemctl restart navbot
sudo install -o root -g root -m 0755 /opt/navbot/deploy/navbot-backup.py /usr/local/sbin/navbot-backup.py
sudo install -o root -g root -m 0644 /opt/navbot/deploy/navbot-telegram.service /etc/systemd/system/navbot-telegram.service
sudo systemctl daemon-reload
sudo systemctl start navbot-backup.service
sudo systemctl enable navbot-telegram.service
sudo systemctl restart navbot-telegram.service
sudo systemctl is-active navbot navbot-telegram
sudo journalctl -u navbot-telegram -n 30 --no-pager
```

Muhim: mavjud backup xizmatingizdagi `ExecStart` yo‘lini `systemctl cat navbot-backup.service` bilan tekshiring. Agar unda boshqa skript yo‘li bo‘lsa, yangilangan backup skriptini o‘sha yo‘lga o‘rnating. Yangi backup ikki SQLite yozuvchisini — asosiy tizim va Telegram xizmatini — to‘xtatib, nusxa olingach avvalgi ishlayotgan holatiga qaytaradi.

Bot Telegramga tashqi **HTTPS** ulanish qiladi. Serverda DNS va tashqi TCP 443 ochiq bo‘lishi kerak. Bot uchun yangi kiruvchi port yoki sayt HTTPS sozlamasi shart emas; saytni HTTPS qilish alohida ish. Token bo‘lmasa yoki integratsiya o‘chirilgan bo‘lsa, worker tashqi so‘rov yubormaydi. Kod o‘zgartirish serverga nashr qilish yoki xizmatni avtomatik yoqish hisoblanmaydi.

Holatni Integratsiyalar bo‘limidan ko‘ring. `409` — webhook yoki ikkinchi polling jarayonini tekshiring; `401` — token; `403` — talaba botni bloklagan bo‘lishi mumkin. `bot_identity_changed` — saqlangan token boshqa botga tegishli: eski chat bog‘lanishlarini boshqa botga avtomatik ko‘chirishga ruxsat berilmaydi. Botni almashtirishni alohida migratsiya sifatida bajaring.

Worker bitta nusxada fayl qulfi bilan ishlaydi. Kiruvchi update raqami va javob navbati SQLite tranzaksiyasida saqlanadi. Tasdiq hodisasi uchun navbat qayta yaratilmaydi; talabaga o‘z tugmasi bilan javobni qayta ochish alohida so‘rovdir. Server qayta ishga tushganda navbat saqlanadi. Bot matnlarini DBdagi navbat nusxalaridan 7 kundan keyin tozalaydi; tasdiqlangan javob esa murojaat saqlanganicha mavjud.

## Sinov

`python3 -m unittest discover -s tests -p 'test_telegram*.py' -v`

Testlar haqiqiy Telegramga ulanmaydi. Token qo‘yilgach, alohida sinov talaba va bot bilan `/start` → kod → murojaatlar → rahbar tasdig‘i → tanlangan fayl jarayonini amalda tekshirish kerak. Ishchi talabalarga test xabari yubormang.
