# Telegram dizayni

## Mini Appga tez kirish

Telegram worker saqlangan Mini App manzilini `setChatMenuButton` orqali chat menyusiga **NAVBOT** tugmasi sifatida avtomatik o‘rnatadi. Manzil o‘zgarsa tugma yangilanadi; bo‘shatilsa odatiy Telegram menyusi qaytadi. API xatosida chat ishlashda davom etadi va sozlash keyinroq takrorlanadi.

Profilga **Ilovani ochish** tugmasi uchun bot egasi **@BotFather → /mybots → kerakli bot → Bot Settings → Configure Mini App → Enable Mini App** orqali `https://navbot.tsuull.uz/student` manzilini kiritadi. Telegram interfeysida nomlar farq qilishi mumkin; Main Mini App sozlamasini tanlang. Bu profil tugmasi Bot API orqali o‘rnatilmaydi. **Xabar yuborish** tugmasi esa Telegram chatini ochishda davom etadi.

Bot xabarlari tartibli kartalar, holat belgilari va sahifalangan murojaatlar bilan yangilandi. Mini App shaxsiy bosh sahifa, to‘rtta xizmat kartasi, pastki navigatsiya, jarayon lentasi, uch til va Telegram mavzusiga mos yorug‘/qorong‘i ko‘rinishga ega.

Talabani kod bilan bog‘lash, imzolangan Telegram initData, murojaat egaligi va faqat tasdiqlangan javob/fayllarni ko‘rsatish talablari saqlangan. Yangi foydalanuvchi ham `/start` orqali inline WebApp tugmasini oladi; tugma o‘zi hisobni bog‘lamaydi.

## Serverga chiqarish

O‘zgarishlar repozitoriyga chiqarilgandan keyin serverda:

```sh
sudo git -C /opt/navbot pull --ff-only
sudo systemctl restart navbot
sudo systemctl restart navbot-telegram
```

Administrator panelidagi Telegram Mini App manzili `https://navbot.tsuull.uz/student` bo‘lishi kerak. Mavjud bot tokenini saqlang. Boshqa tashkilotlar o‘z HTTPS domenini ishlatadi. TLS Kerio reverse proxy orqali ishlaydi; ichki server `172.20.30.31:80` bo‘lib qoladi.

Telegramda `/start` yuboring va yangi inline ilova tugmasini bosing. Eski xabarlar qayta chizilmaydi. Mini App ochiq bo‘lsa, uni yopib qayta oching.

Oddiy brauzerda `/student` ochilganda Telegram tasdiqlashi talab qilinishi kutilgan holat. `?demo=1` faqat sun’iy ma’lumotli dizayn namunasidir. Reply keyboard o‘rniga inline WebApp tugmasi imzolangan initData bilan ishga tushiradi.

## Tekshirish

Avtomatik tekshiruvlar soxta Telegram tokeni va imzolangan test ma’lumotlaridan foydalanadi; haqiqiy foydalanuvchilarga xabar yubormaydi. Yangilashdan keyin telefonda `/start`, hisobni bog‘lash, murojaatlar, jarayon, tasdiqlangan fayl, profil, uch til va mavzu almashishini tekshiring.
