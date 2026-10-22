# ZarinaAssistent — tug‘ilgan kun boti

Ishxona guruhida xodimlarni tug‘ilgan kuni bilan avtomatik tabriklaydi. Adminlar bot orqali boshqaradi.

## Ishga tushirish

1. @BotFather da bot yarating, tokenni oling. `/setprivacy` → Disable shart emas (bot faqat `/setgroup` ni o‘qiydi).
2. `.env.example` ni `.env` ga nusxalang va `BOT_TOKEN`, `SUPER_ADMINS` ni to‘ldiring.
3. Serverda:
   ```bash
   docker compose up -d --build
   ```
   yoki Docker siz:
   ```bash
   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   .venv/bin/python -m bot
   ```
4. Birinchi ishga tushishda `ZarinaBirthdayBot.xls` dagi xodimlar bazaga yuklanadi.
5. Botni guruhga qo‘shing va guruhda `/setgroup` yozing.

Baza: `data/bot.db` (SQLite) — zaxira nusxa uchun shu faylni saqlang.

## Imkoniyatlar

- Xodimlar ro‘yxati, qo‘shish, tahrirlash, o‘chirish
- Lotin va kirillda qidirish (`Хамраев` = `Xamrayev` = `Hamraev`)
- Erkak / ayol uchun alohida shablonlar, 3 tilda; har safar tasodifiy shablon
- Tabrik tili va yuborish vaqti sozlamalardan
- Excel import (qo‘shish yoki to‘liq yangilash) va export
- Adminlarga kunlik hisobot va ertangi tug‘ilgan kunlar ro‘yxati
- 29-fevralda tug‘ilganlar oddiy yilda 28-fevralda tabriklanadi
- Bot o‘chib qolsa, yoqilganda o‘sha kungi tabriklarni yuboradi (ikki marta yubormaydi)
