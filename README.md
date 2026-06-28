# 📚 Online Kutibxona (Raqamli Kutubxona)

Zamonaviy maktablar uchun mo'ljallangan, QR-kod tizimi orqali ishlaydigan aqlli kutubxona boshqaruv tizimi.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)
![Django](https://img.shields.io/badge/django-5.0%2B-green.svg)

## ✨ Asosiy imkoniyatlar

*   🛡️ **Xavfsiz dinamik QR-kodlar:** Har 2 daqiqada yangilanadigan HMAC asosidagi xavfsiz identifikatsiya tizimi.
*   👨‍💼 **Ko'p darajali boshqaruv:**
    *   **Super Admin:** Barcha maktablarni va muassasalarni nazorat qilish.
    *   **Maktab Admini (Kutubxonachi):** Kitoblar fondini boshqarish, o'quvchilarni ro'yxatga olish va kitob berish/qabul qilish.
    *   **O'quvchi/O'qituvchi:** Kitoblarni qidirish, bron qilish va shaxsiy kabinet orqali o'z kitoblarini kuzatish.
*   🎨 **Premium Dizayn:** Zamonaviy "Glassmorphism" uslubidagi qulay interfeys.
*   📸 **Kamera bilan ishlash:** QR skaner orqali kitob berish va qabul qilish.
*   📊 **Real-vaqt statistikasi:** Kitoblar aylanishi va o'quvchilar faolligini tahlil qilish.
*   🌍 **Ko'p tilli qo'llab-quvvatlash:** O'zbek, Rus, Ingliz va Qaraqalpaq tillari.

## 🏗️ Loyiha strukturasi (Architecture)

Loyiha modulli arxitekturaga asoslangan bo'lib, har bir rol uchun alohida frontend ilovalari mavjud:

```text
ebook/
├── core/                 # Sozlamalar va global marshrutlash
├── accounts/             # Foydalanuvchilar, rollar va xavfsizlik (HMAC Tokens)
├── schools/              # Maktablar va muassasalar bazasi
├── books/                # Kitoblar katalogi, inventar va ijara tizimi
├── stats/                # Tizim loglari va tahliliy ma'lumotlar
├── notifications/        # Push-bildirishnomalar va xabarlar
├── frontend_admin/       # Super Admin interfeysi (Django Templates)
├── frontend_school/      # Maktab Admini/Kutubxonachi interfeysi
├── frontend_user/        # O'quvchi va O'qituvchi interfeysi
├── static/               # Global CSS/JS va dizayn aktivlari
├── templates/            # Umumiy va asosiy shablonlar (Base layouts)
├── locale/               # Tarjima fayllari (.po / .mo)
├── media/                # Yuklangan rasmlar va QR-kodlar
└── README.md             # Loyiha hujjatlari
```

## 🛠️ Texnologiyalar

*   **Backend:** Python 3.12+, Django 5.0+, SQLite (development) / PostgreSQL (production)
*   **Frontend:** Vanilla JS, HTML5, CSS3 (Glassmorphism design)
*   **QR System:** HMAC-based dynamic tokens + html5-qrcode (JS)
*   **UI Framework:** Jazzmin (Admin panel uchun)

## 🚀 O'rnatish

1.  **Loyiha nusxasini olish:**
    ```bash
    git clone https://github.com/username/elektron-kutibxona.git
    cd elektron-kutibxona
    ```

2.  **Virtual muhitni sozlash:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows uchun: venv\Scripts\activate
    ```

3.  **Kutubxonalarni o'rnatish:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Bazani tayyorlash:**
    ```bash
    python manage.py migrate
    ```

5.  **Admin foydalanuvchi yaratish:**
    ```bash
    python manage.py createsuperuser
    ```

6.  **Loyihani ishga tushirish:**
    ```bash
    python manage.py runserver
    ```

## 🌐 Tarjimalarni yangilash

```bash
# Yangi tarjimalarni qo'shgandan so'ng kompilyatsiya qilish:
python -c "import polib; import os; \
  for lang in ['ru','en','kaa']: \
    po = polib.pofile(f'locale/{lang}/LC_MESSAGES/django.po'); \
    po.save_as_mofile(f'locale/{lang}/LC_MESSAGES/django.mo')"
```

## 📄 Litsenziya

Ushbu loyiha MIT litsenziyasi ostida tarqatiladi.

---
Developed with ❤️ for Modern Schools.
