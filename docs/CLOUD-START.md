# Bulutdagi keyingi ishlar uchun boshlash yo‘riqnomasi

Mavjud `/workspace/NavBot` checkoutdan foydalaning. Har cloud task alohida muhitda; foydalanuvchi so‘ramasa Git worktree yaratmang.

Python 3.12+ standart kutubxonalari yetarli. README.md, docs/ACCEPTANCE.md va git statusni tekshiring. Ilova paketlarini o‘rnatish talab qilinmaydi.

```sh
cd /workspace/NavBot
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 navbot/app.py --port 8081 --db /tmp/navbot-local.sqlite3 --seed-demo
```

Mavjud ishlayotgan server bo‘lsa uning porti va bazasini tekshirmasdan ikkinchisini ishga tushirmang. Foydalanuvchi bazasini almashtirmang. Demo bazasi faqat sun’iy ma’lumotli lokal sinov uchun.

Readiness: `/api/catalog` va `/kiosk` HTTP200. `/login`, `/manager`, `/tv`, `/tablo?id=1` orqali oqimni tekshiring. Hisoblar va testlar READMEda. `node tests/workflow-browser.cjs` o‘zining vaqtinchalik server/bazasini yaratadi va yakunda to‘xtatadi (Playwright+Chromium mavjud bo‘lsa).

Processlar yangi cloud taskda qayta ishga tushiriladi. Real HEMIS/LMS/Telegram va jismoniy qurilmalar ulanmagan. Deploy/publish foydalanuvchining tegishli ko‘rsatmasi bilan amalga oshiriladi.

**Konfiguratsiya holati:** 2026-11-17 kuni `start_skill` maydonini shu yangi oqimga yangilash server tomonidan `draft_not_editable` bilan rad etildi. Saqlash tasdiqlanmadi; amaldagi muhit sozlamasi bo‘sh repo haqidagi eski yo‘riqnomani saqlashi mumkin. Taklif qilingan yangi boshlash tartibi ushbu faylda va READMEda saqlangan. Bu ilova kodi yoki lokal ishga tushirishga to‘sqinlik qilmaydi.
