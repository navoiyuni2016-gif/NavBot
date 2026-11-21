# Dashboard va kunlik navbat yangilanishi

Yangilanish mavjud talabalar, murojaatlar, cheklar, audio va tarixni saqlaydi.
Xizmatlar katalogidagi standart nomlar yangilanadi; oldingi chek matni saqlanadi.

- Dashboard: sohalar, fakultetlar va kurslar kesimi; fakultet/kurs filtrlari;
  oxirgi 7 kun dinamikasi. Umumiy hisoblar barcha sanalarni qamrab oladi.
  Talaba biriktirilmagan murojaatlar alohida ko‘rsatiladi.
- PNG/PDF tugmalari tanlangan kesimning umumlashtirilgan hisobotini yuklaydi.
- Rahbar va superadmin: **Menejerlar qabuli** orqali sabab bilan bloklash/tiklash.
  Bloklangan menejer kirishi va ko‘rishi mumkin; qabul, qayta chaqirish, tahrirlash,
  yangi murojaat, fayl va Telegram amallari serverda rad qilinadi. Audit saqlanadi.
  Joriy qabul o‘z-o‘zidan yopilmaydi; zarur bo‘lsa rahbar qabulni tiklaydi.
- Bo‘limi bo‘sh bo‘lgan murojaatga mavjud mas’ul yoki menejerning bo‘limi tiklanadi.
  Mas’ulsiz murojaatga bo‘lim taxminan belgilanmaydi.
- Har bir harf uchun raqam Toshkent vaqti bilan yangi kuni 001 dan boshlanadi.
  Oldingi cheklar o‘chmaydi, eski raqamlar o‘zgarmaydi. Oldingi kun cheklari
  TV va menejer oynasida sanasi bilan ko‘rsatiladi. Arizaning NAV raqami qayta
  boshlanmaydi. Takror so‘rov o‘sha chekni qaytaradi, yangi chek yaratmaydi.

Joylashtirishdan oldin mavjud zaxira xizmatini ishga tushirib muvaffaqiyatini
tekshiring. Keyin kodni yangilab `navbot` xizmatini qayta ishga tushiring.
Migratsiya birinchi ishga tushishda bazaning `.pre-v05-*.bak` nusxasini ham yaratadi.
Tozalash skriptini ishlatmang. Brauzerni yangilang; APKni almashtirish talab qilinmaydi.

Migratsiyadan keyin bir xil raqam ikki xil sanada bo‘lishi mumkin. Eski kodga
qaytishdan oldin xizmatlarni to‘xtatib, yangilanishdan oldingi bazani tiklash talab
etiladi; bu orada yaratilgan haqiqiy murojaatlarni yo‘qotmasdan ko‘chirish lozim.
Faqat eski kodni qayta qo‘yish xavfsiz orqaga qaytish hisoblanmaydi.
