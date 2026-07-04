"""Fast demo data generator for Karakalpakstan school library system."""
import django, os, sys, random
from datetime import date, timedelta

sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'
django.setup()

from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.db import transaction

from accounts.models import CustomUser
from schools.models import District, School, Subject, Institution
from books.models import (
    Category, Book, BookIssue, TextbookLoan, BookRequest, BookWaitlist,
    Achievement, UserAchievement, Challenge, UserChallenge, ReaderOfMonth,
)
from frontend_school.models import News, GradePromotionLog
from notifications.models import Notification, PushSubscription
from stats.models import ActionLog

print("=== Clearing existing data ===")
models = [BookIssue, BookRequest, BookWaitlist, TextbookLoan, UserAchievement,
          UserChallenge, ReaderOfMonth, Challenge, Achievement, Notification,
          PushSubscription, ActionLog, News, GradePromotionLog,
          CustomUser, Book, Category, Subject, School, District, Institution]
for m in models:
    try:
        m.objects.all().delete()
    except Exception:
        pass
print("Cleared.")

# ── DISTRICTS ──
print("Creating districts...")
dist_names = ['Amudaryo', 'Beruniy', 'Qanliko\'l', 'Qorao\'zak', 'Kegeyli',
              'Qo\'ng\'irot', 'Mo\'ynoq', 'Nukus', 'Tahiatosh', 'Taxtako\'pir',
              'To\'rtko\'l', 'Xojeli', 'Chimboy', 'Shomanay', 'Ellikqal\'a', 'Bo\'zataw']
districts = {n: District.objects.create(name=n) for n in dist_names}
print(f"  {len(districts)} districts")

# ── SCHOOLS ──
print("Creating schools...")
school_names = {
    'Amudaryo': 2, 'Beruniy': 2, 'Qanliko\'l': 1, 'Qorao\'zak': 2, 'Kegeyli': 2,
    'Qo\'ng\'irot': 2, 'Mo\'ynoq': 1, 'Nukus': 5, 'Tahiatosh': 1, 'Taxtako\'pir': 1,
    'To\'rtko\'l': 2, 'Xojeli': 2, 'Chimboy': 1, 'Shomanay': 1, 'Ellikqal\'a': 1, 'Bo\'zataw': 1,
}
schools = []
for dn, cnt in school_names.items():
    for i in range(cnt):
        s = School(name=f"{dn} {i+1}-son maktab", address=f"{dn} tumani", contact="+998901234567", district=districts[dn])
        schools.append(s)
School.objects.bulk_create(schools)
schools = list(School.objects.all())
print(f"  {len(schools)} schools")

# ── SUBJECTS ──
print("Creating subjects...")
subj_names = ['Algebra', 'Geometriya', 'Fizika', 'Kimyo', 'Biologiya', 'Ona tili',
              'Adabiyot', 'Rus tili', 'Ingliz tili', 'Nemis tili', 'Tarix', 'Huquq',
              'Geografiya', 'Informatika', 'Jismoniy tarbiya', 'Matematika',
              'Qoraqalpoq tili', 'Qoraqalpoq adabiyoti', 'Tabiiy fanlar', 'Musiqa',
              'Chizmachilik', 'Astronomiya', 'Ekologiya', 'San\'at']
Subject.objects.bulk_create([Subject(name=n) for n in subj_names])
subjects = {s.name: s for s in Subject.objects.all()}
print(f"  {len(subjects)} subjects")

# ── CATEGORIES ──
print("Creating categories...")
cat_names = ['Badiiy', 'Ilmiy', 'Darslik', 'Lug\'at', 'Ensiklopediya', 'Bolalar', 'Tarixiy', 'She\'riyat', 'Qo\'llanma', 'Sarguzasht']
Category.objects.bulk_create([Category(name=n) for n in cat_names])
categories = list(Category.objects.all())
print(f"  {len(categories)} categories")

# ── ADMINS ──
print("Creating admins...")
admins = []
pw = make_password('admin123')
for s in schools:
    u = CustomUser(username=f'admin{s.id}', password=pw, first_name=f'Admin{s.id}',
                   last_name=f'Maktab', role='school_admin', school=s)
    admins.append(u)
CustomUser.objects.bulk_create(admins)
print(f"  {len(admins)} admins")

# ── TEACHERS ──
print("Creating teachers...")
teachers = []
pw_t = make_password('teacher123')
all_subj_names = list(subjects.keys())
for s in schools:
    for j in range(random.randint(3, 5)):
        subj = random.choice(all_subj_names)
        u = CustomUser(username=f'teacher{s.id}_{j}', password=pw_t,
                       first_name=f"O'qit.{subj[:5]}", last_name=f"Sch{s.id}",
                       role='teacher', school=s, subject=subj)
        teachers.append(u)
CustomUser.objects.bulk_create(teachers)
print(f"  {len(teachers)} teachers")

# ── STUDENTS ──
print("Creating students...")
first_names = ['Aziz','Bekzod','Davron','Eldor','Farrux','Husan','Ilhom','Jasur',
               'Kamol','Laziz','Mirzo','Nodir','Otabek','Rustam','Sanjar','Temur',
               'Ulug\'bek','Xurshid','Zafar','Akmal','Botir','Dilmurod','Erkin',
               'Furqat','G\'ofur','Hakim','Islom','Javohir','Karim','Murod',
               'Nasim','Ravshan','Sardor','To\'lqin','Umid','Xasan','Yoqub','Zohid',
               'Adolat','Barno','Charos','Dildora','Feruza','Gulnoza','Hilola',
               'Iroda','Jamila','Kamola','Lola','Nigora','Odina','Rano','Sabina',
               'Umida','Yulduz','Zamira','Bonu','Diyora','Fotima','Gulbahor','Intizor']
grades = [str(g) for g in range(1, 12)]
students = []
pw_s = make_password('student123')
for s in schools:
    for j in range(random.randint(30, 55)):
        g = random.choice(grades)
        fn = random.choice(first_names)
        u = CustomUser(username=f'student{s.id}_{j}', password=pw_s,
                       first_name=fn, last_name=f"Fam{s.id}_{j}",
                       role='student', school=s, grade=g,
                       birth_date=date(2016-int(g) if int(g) < 11 else 2005,
                                       random.randint(1,12), random.randint(1,28)),
                       xp_points=random.randint(0, 500), level=random.randint(1, 10),
                       total_books_read=random.randint(0, 25))
        students.append(u)
CustomUser.objects.bulk_create(students)
students = list(CustomUser.objects.filter(role='student'))
print(f"  {len(students)} students")

# ── BOOKS (~1000 total) ──
print("Creating books...")
BATCH = 200
book_objects = []
textbooks_by_gs = {}
target_textbooks = 600
target_regular = 400

# Distribute textbooks across schools/grades
textbook_subjects = ['Matematika', 'Ona tili', 'Adabiyot', 'Ingliz tili', 'Fizika', 'Kimyo', 'Biologiya', 'Tarix', 'Geografiya']
per_school_grade = max(1, target_textbooks // (len(schools) * 11))

for school in schools:
    for grade_num in range(1, 12):
        gs = (school.id, grade_num)
        num_per_grade = per_school_grade if grade_num <= 9 else 0
        for _ in range(num_per_grade):
            sn = random.choice(textbook_subjects)
            cnt = random.randint(20, 50)
            b = Book(school=school, title=f"{sn} {grade_num}-sinf", author=sn,
                     description=f"{sn} darsligi {grade_num}-sinf", category=categories[random.randint(0, min(3, len(categories)-1))],
                     total_count=cnt, available_count=random.randint(5, cnt-5), is_textbook=True,
                     subject=sn, grade=grade_num)
            book_objects.append(b)
            textbooks_by_gs.setdefault(gs, []).append(b)
            if len(book_objects) >= BATCH:
                Book.objects.bulk_create(book_objects)
                book_objects = []

# Regular books
reg_per_school = max(1, target_regular // len(schools))
for school in schools:
    for _ in range(reg_per_school):
        cnt = random.randint(2, 10)
        b = Book(school=school, title=f"Kitob #{random.randint(1000, 9999)}",
                 author=random.choice(['Alisher Navoiy','Oybek','G\'afur G\'ulom',
                                       'O\'tkir Hoshimov','Chingiz Aytmatov','Jack London']),
                 description="Badiiy kitob", category=random.choice(categories),
                 total_count=cnt, available_count=random.randint(0, cnt), is_textbook=False)
        book_objects.append(b)
        if len(book_objects) >= BATCH:
            Book.objects.bulk_create(book_objects)
            book_objects = []

if book_objects:
    Book.objects.bulk_create(book_objects)

books = list(Book.objects.all())
total = len(books)
tb_count = Book.objects.filter(is_textbook=True).count()
print(f"  {total} books (textbooks: {tb_count}, regular: {total - tb_count})")

# ── TEXTBOOK LOANS ──
print("Creating textbook loans...")
tloans = []
academic_year = "2025/2026"
due = date(2026, 6, 1)
# Reload textbooks_by_gs with real IDs
textbooks_by_gs.clear()
for b in Book.objects.filter(is_textbook=True).only('id', 'school_id', 'grade'):
    gs = (b.school_id, b.grade)
    textbooks_by_gs.setdefault(gs, []).append(b)

for student in students:
    if not student.grade or not student.school_id:
        continue
    gn = ''.join(c for c in (student.grade or '') if c.isdigit())
    if not gn:
        continue
    gs = (student.school_id, int(gn))
    tbs = textbooks_by_gs.get(gs, [])
    for tb in tbs:
        if random.random() < 0.12:
            continue
        tloans.append(TextbookLoan(book_id=tb.id, student=student, due_date=due,
                                    condition_on_issue=random.choice(['new','good','fair']),
                                    academic_year=academic_year,
                                    returned_at=date(2026, random.randint(1,5), random.randint(1,28))
                                    if random.random() < 0.08 else None))
        if len(tloans) >= BATCH:
            TextbookLoan.objects.bulk_create(tloans, ignore_conflicts=True)
            tloans = []
if tloans:
    TextbookLoan.objects.bulk_create(tloans, ignore_conflicts=True)
print(f"  {TextbookLoan.objects.count()} loans")

# ── BOOK ISSUES ──
print("Creating book issues...")
issues = []
regular_ids = [b.id for b in books if not b.is_textbook]
for student in students[:min(len(students), 300)]:
    for bk_id in random.sample(regular_ids, min(random.randint(0, 10), len(regular_ids))):
        issued = timezone.now() - timedelta(days=random.randint(1, 365))
        returned = issued + timedelta(days=random.randint(3, 30)) if random.random() < 0.8 else None
        issues.append(BookIssue(book_id=bk_id, user=student, issued_at=issued,
                                returned_at=returned, is_returned=returned is not None))
        if len(issues) >= BATCH:
            BookIssue.objects.bulk_create(issues)
            issues = []
if issues:
    BookIssue.objects.bulk_create(issues)
print(f"  {BookIssue.objects.count()} issues")

# ── ACHIEVEMENTS ──
print("Creating achievements...")
ach_defs = [
    ('first_book', 'Birinchi kitob', 'Birinchi kitob o\'qildi', 'fa-book', 10, 'books_count', 1),
    ('five_books', 'Besh kitob', '5 ta kitob o\'qildi', 'fa-book-open', 25, 'books_count', 5),
    ('ten_books', 'O\'n kitob', '10 ta kitob o\'qildi', 'fa-star', 50, 'books_count', 10),
    ('twenty_books', 'Yigirma kitob', '20 ta kitob o\'qildi', 'fa-trophy', 100, 'books_count', 20),
    ('fifty_books', 'Ellik kitob', '50 ta kitob o\'qildi', 'fa-crown', 200, 'books_count', 50),
    ('week_streak', 'Haftalik streak', '7 kun ketma-ket o\'qish', 'fa-fire', 30, 'streak', 7),
    ('two_week_streak', 'Ikki haftalik streak', '14 kun ketma-ket o\'qish', 'fa-fire', 60, 'streak', 14),
]
Achievement.objects.bulk_create([
    Achievement(key=k, name=n, description=d, icon=i, xp_reward=x, condition_type=ct, condition_value=cv)
    for k, n, d, i, x, ct, cv in ach_defs
])
achievements = list(Achievement.objects.all())
print(f"  {len(achievements)} achievements")

# ── CHALLENGES ──
print("Creating challenges...")
Challenge.objects.bulk_create([
    Challenge(title=f"O'qish marafoni {i}", description=f"Bu oyda {5+i*5} ta kitob o'qing!",
              challenge_type='books_count', target_count=5+i*5, xp_reward=50+i*25,
              start_date=date(2026,1,1), end_date=date(2026,12,31), school=schools[i])
    for i in range(min(5, len(schools)))
    for _ in range(2)
])
print(f"  {Challenge.objects.count()} challenges")

# ── NEWS ──
print("Creating news...")
news_titles = ['Kutubxona yangi kitoblar bilan to\'ldirildi',
               'O\'quvchilar orasida kitob o\'qish marafoni boshlandi',
               'Eng faol o\'quvchi aniqlandi',
               'Darslik tarqatish boshlandi',
               'She\'riyat kechasi o\'tkazildi',
               'Kitob ko\'rgazmasi ochildi']
news_list = []
for s in schools:
    for t in random.sample(news_titles, random.randint(2, 4)):
        news_list.append(News(school=s, title=t, body=f"{t}. Maktabimizdagi muhim voqea.",
                               is_published=True,
                               created_at=timezone.now()-timedelta(days=random.randint(1,60))))
News.objects.bulk_create(news_list)
print(f"  {len(news_list)} news")

print("\n=== DEMO DATA CREATED SUCCESSFULLY ===")
print(f"  Districts: {District.objects.count()}")
print(f"  Schools:   {School.objects.count()}")
print(f"  Subjects:  {Subject.objects.count()}")
print(f"  Admins:    {CustomUser.objects.filter(role='school_admin').count()}")
print(f"  Teachers:  {CustomUser.objects.filter(role='teacher').count()}")
print(f"  Students:  {CustomUser.objects.filter(role='student').count()}")
print(f"  Books:     {Book.objects.count()} (textbooks: {Book.objects.filter(is_textbook=True).count()})")
print(f"  TB Loans:  {TextbookLoan.objects.count()}")
print(f"  Issues:    {BookIssue.objects.count()}")
print(f"  Achiev:    {Achievement.objects.count()}")
print(f"  Challenges:{Challenge.objects.count()}")
print(f"  News:      {News.objects.count()}")
