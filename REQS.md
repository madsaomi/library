# 📚 Online Kutibxona — AI Agent README

Полное техническое задание для ИИ агента на разработку системы онлайн-библиотеки школ.

---

## 🏗️ Архитектура проекта

```
online_kutibxona/
├── core/                 # Настройки, urls, wsgi
├── accounts/             # Пользователи, роли, авторизация
├── schools/              # Школы, учреждения
├── books/                # Книги, категории, выдача
├── stats/                # Статистика
├── frontend_admin/       # Django Templates — Super Admin панель
├── frontend_school/      # Django Templates — School Admin панель
└── frontend_user/        # Django Templates — Ученик/Учитель интерфейс
```

**Стек:**
- Backend: Django 5.x + Django REST Framework
- Frontend: HTML + Bootstrap 5 + Vanilla JS (Django Templates)
- БД: PostgreSQL
- QR: `qrcode` Python библиотека
- Auth: Django Session Auth (не JWT)

---

## 👤 Роли пользователей

| Роль | Описание |
|------|----------|
| `superuser` | Один на всю систему. login: `admin`, password: `superadmin` |
| `school_admin` | Администратор конкретной школы. Логин/пароль получает от superuser |
| `student` | Ученик школы. Логин авто-генерируется, пароль случайный 8–16 символов |
| `teacher` | Учитель школы. Аналогично ученику |

---

## 🔐 Авторизация

- При входе с логином/паролем система определяет роль и перенаправляет:
  - `superuser` → `/admin-panel/`
  - `school_admin` → `/school-panel/`
  - `student` / `teacher` → `/library/`
- Все панели закрыты — редирект на `/login/` если не авторизован

---

## 🛡️ SUPER ADMIN панель (`/admin-panel/`)

### Доступ
Только один superuser в системе.

### Меню и функционал

#### 1. Школы (`/admin-panel/schools/`)
- **Добавить школу** — форма: название, адрес, контакт
- **Просмотр списка школ** — таблица со школами
  - Кнопка **Просмотр** → карточка школы:
    - Информация о школе
    - Количество книг
    - Категории книг
    - Количество классов
    - Учителя
    - Кнопка **Удалить** → модальное окно подтверждения (`Подтвердить` / `Отмена`)

#### 2. Учреждения (`/admin-panel/institutions/`)
- **Добавить учреждение**
- **Просмотр списка учреждений**

#### 3. Статистика (`/admin-panel/statistics/`)
- Общая сводка по системе (книги, ученики, учителя, школы)

#### 4. Последние действия (`/admin-panel/activity/`)
- Лог последних операций в системе

---

## 🏫 SCHOOL ADMIN панель (`/school-panel/`)

### Доступ
Неограниченное количество school admin-ов. Логин/пароль выдаёт superuser.

### Меню и функционал

#### 1. Личный кабинет
- Смена пароля

#### 2. Выдача книги (`/school-panel/issue-book/`)
- Открывается QR-сканер
- Сканирует QR-код ученика или учителя
- Отображает данные пользователя
- Подтверждение выдачи → `book.count -= 1` в БД

#### 3. Приём книги (`/school-panel/return-book/`)
- Открывается QR-сканер
- Сканирует QR-код книги
- Принять возврат → `book.count += 1` в БД

#### 4. Книги на руках (`/school-panel/issued-books/`)
- Список всех выданных книг (кому, когда, какая книга)

#### 5. Ученики (`/school-panel/students/`)
- **Добавить ученика** — форма:
  - Имя (`name`)
  - Фамилия (`surname`)
  - Дата рождения (`birthday`)
  - Логин — **автогенерируется** (привязан к школе + классу)
  - Пароль — **случайный**, 8–16 символов, уникальный
  - После сохранения: сообщение `"Данные добавлены"`
- **Изменить ученика**:
  - Сначала выбрать класс (фильтр)
  - Список учеников отсортирован по алфавиту (на латинице)
  - Формат: `1. Alimov Jasur | Просмотр | Изменить`
  - **Просмотр** → все данные ученика (имя, фамилия, дата рождения, логин, пароль)
  - **Изменить** → редактирование данных

#### 6. Учителя (`/school-panel/teachers/`)
- **Добавить учителя** — форма:
  - Имя (`name`)
  - Фамилия (`surname`)
  - Дата рождения (`birthday`)
  - Адрес проживания
  - Должность/специальность
  - Логин — **автогенерируется** (привязан к школе, с пометкой "учитель")
  - Пароль — **случайный**, 8–16 символов, уникальный
  - После сохранения: сообщение `"Добавлено"`
- **Изменить учителя**:
  - Список отсортирован по алфавиту (латиница)
  - **Просмотр** / **Изменить** — аналогично ученикам

#### 7. Книги (`/school-panel/books/`)
- **Добавить книгу** — форма:
  - Название книги
  - Биография / описание
  - Фото обложки
- **Изменить** — редактирование существующей книги
- **Просмотр** — детальная страница книги с возможностью редактирования

#### 8. Новости (`/school-panel/news/`)
- **Просмотр** — список новостей
- **Изменить** — редактирование новости
- Видимость (опубликовать / скрыть)

---

## 📖 ИНТЕРФЕЙС УЧЕНИКА / УЧИТЕЛЯ (`/library/`)

### Доступ
Логин и пароль, полученные от school admin.

### Функционал

#### Главная страница
- Список книг школьной библиотеки
- Сортировка: самые популярные книги (часто берут) — первые
- Поиск книг через `search` поле

#### Мои книги
- Список книг, которые сейчас на руках у пользователя
- Дата выдачи
- Кнопка **Сдать** → показывает QR-код книги → school admin сканирует QR и принимает книгу

#### Взять книгу
- Ученик/учитель находит книгу в каталоге
- School admin сканирует QR-код пользователя → выдаёт книгу
- После выдачи: на экране `"Вы получили книгу [название]"` → главное меню

#### Личный кабинет
- Смена пароля

---

## 🗄️ Модели БД (Django Models)

```python
# accounts/models.py
class User(AbstractUser):
    role = CharField(choices=['superuser', 'school_admin', 'student', 'teacher'])
    school = ForeignKey('School', null=True)
    grade = CharField(null=True)  # класс для ученика

# schools/models.py
class School(Model):
    name = CharField()
    address = CharField()
    contact = CharField()

class Institution(Model):
    name = CharField()
    address = CharField()

# books/models.py
class Category(Model):
    name = CharField()

class Book(Model):
    school = ForeignKey(School)
    title = CharField()
    description = TextField()
    cover = ImageField()
    category = ForeignKey(Category)
    total_count = IntegerField()
    available_count = IntegerField()
    borrow_count = IntegerField(default=0)  # для сортировки по популярности

class BookIssue(Model):
    book = ForeignKey(Book)
    user = ForeignKey(User)
    issued_at = DateTimeField(auto_now_add=True)
    returned_at = DateTimeField(null=True)
    is_returned = BooleanField(default=False)

# news (внутри school_admin)
class News(Model):
    school = ForeignKey(School)
    title = CharField()
    body = TextField()
    is_published = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
```

---

## 🔢 Логика генерации логинов и паролей

### Логин ученика
```
Формат: {school_id}_{grade}_{порядковый_номер}
Пример: 12_9b_003
```

### Логин учителя
```
Формат: {school_id}_t_{порядковый_номер}
Пример: 12_t_007
```

### Пароль (для всех)
```python
import random, string
def generate_password(length=None):
    if length is None:
        length = random.randint(8, 16)
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))
# Проверить уникальность в БД перед сохранением
```

---

## 📷 QR-код логика

### Генерация QR для пользователя
```python
import qrcode
# QR содержит: user_id или уникальный токен пользователя
qr = qrcode.make(str(user.id))
qr.save(f"media/qr/user_{user.id}.png")
```

### Генерация QR для книги
```python
qr = qrcode.make(str(book.id))
qr.save(f"media/qr/book_{book.id}.png")
```

### Сканирование (frontend)
- Использовать библиотеку `html5-qrcode` (JS, CDN)
- При сканировании QR пользователя → GET `/api/user/{id}/` → показать данные → подтвердить выдачу
- При сканировании QR книги → GET `/api/book/{id}/` → подтвердить приём

---

## 🌐 URL структура

```
/login/                          → Общий вход
/logout/                         → Выход

# Super Admin
/admin-panel/                    → Дашборд
/admin-panel/schools/            → Школы
/admin-panel/schools/add/        → Добавить школу
/admin-panel/schools/<id>/       → Просмотр школы
/admin-panel/schools/<id>/delete/→ Удалить школу
/admin-panel/institutions/       → Учреждения
/admin-panel/statistics/         → Статистика
/admin-panel/activity/           → Последние действия

# School Admin
/school-panel/                   → Дашборд
/school-panel/issue-book/        → Выдать книгу (QR)
/school-panel/return-book/       → Принять книгу (QR)
/school-panel/issued-books/      → Книги на руках
/school-panel/students/          → Ученики
/school-panel/students/add/      → Добавить ученика
/school-panel/teachers/          → Учителя
/school-panel/teachers/add/      → Добавить учителя
/school-panel/books/             → Книги
/school-panel/books/add/         → Добавить книгу
/school-panel/news/              → Новости
/school-panel/profile/           → Личный кабинет

# Student / Teacher
/library/                        → Каталог книг
/library/my-books/               → Мои книги
/library/profile/                → Личный кабинет
```

---

## ⚙️ Настройка и запуск

```bash
# 1. Установка зависимостей
pip install django djangorestframework pillow qrcode psycopg2-binary

# 2. Создание superuser
python manage.py createsuperuser
# username: admin | password: superadmin

# 3. Миграции
python manage.py makemigrations
python manage.py migrate

# 4. Запуск
python manage.py runserver
```

---

## 📋 Важные бизнес-правила

1. **Один superuser** — в системе всегда ровно один. Регистрация через `createsuperuser`.
2. **School admin** не ограничен по количеству — superuser создаёт сколько угодно.
3. При **удалении школы** — обязательное модальное подтверждение (2 кнопки: Подтвердить / Отмена).
4. **Выдача книги**: `book.available_count -= 1`, `book.borrow_count += 1`
5. **Приём книги**: `book.available_count += 1`
6. Книги в каталоге сортируются по `borrow_count DESC` (самые популярные первые).
7. Пароли **уникальны** — перед сохранением проверять на совпадение в БД.
8. Логины привязаны к школе и роли — не могут совпадать между разными школами случайно, но система должна это гарантировать уникальностью в БД.

---

## 🔑 Резюме для агента

> Это система управления школьной библиотекой. Три независимые панели на Django Templates (не SPA). Backend на Django. Три типа пользователей с разными правами. QR-сканер для выдачи/приёма книг. Всё в рамках одного Django-проекта, разные приложения для разных ролей.
