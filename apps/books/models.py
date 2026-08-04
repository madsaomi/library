import logging

from django.conf import settings
from django.db import models
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

logger = logging.getLogger(__name__)


def book_search_vector():
    return models.Func(
        Coalesce(models.F('title'), models.Value('')),
        models.Value('A'),
        Coalesce(models.F('author'), models.Value('')),
        models.Value('B'),
        Coalesce(models.F('description'), models.Value('')),
        models.Value('C'),
        function='to_tsvector',
        template="%(function)s('simple', %(expressions)s)",
        arg_joiner=' || ',
        output_field=models.TextField(),
    )


class Category(models.Model):
    name = models.CharField(_('Nomi'), max_length=255)
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Kategoriya')
        verbose_name_plural = _('Kategoriyalar')


class Book(models.Model):
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, verbose_name=_('Maktab'))
    title = models.CharField(_('Sarlavha'), max_length=255)
    author = models.CharField(_('Muallif'), max_length=255, null=True, blank=True)
    description = models.TextField(_('Tavsif'))
    cover = models.ImageField(_('Muqova'), upload_to='book_covers/%Y/%m/%d/', null=True, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Kategoriya'), db_index=True
    )
    total_count = models.IntegerField(_('Umumiy soni'))
    available_count = models.IntegerField(_('Mavjud soni'))
    borrow_count = models.IntegerField(_("O'qilganlar soni"), default=0, db_index=True)
    is_textbook = models.BooleanField(
        _('Darslik'), default=False, help_text=_("Maktab darsligi (o'quvchilarga yilga beriladi)")
    )
    subject = models.CharField(_('Fan'), max_length=100, null=True, blank=True)
    grade = models.IntegerField(
        _('Sinf'), null=True, blank=True, help_text=_("Darslik uchun mo'ljallangan sinf (1-11)")
    )
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)
    history = HistoricalRecords()

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    @property
    def currently_reading_count(self):
        return self.total_count - self.available_count

    def save(self, *args, **kwargs):
        # Image optimization: resize and compress cover only if it's new or changed
        if self.cover:
            try:
                # Check if this is a new file being uploaded
                # (it won't have a value in _committed if it's a new UploadedFile)
                is_new_image = not getattr(self.cover, '_committed', True)

                if is_new_image:
                    import os
                    from io import BytesIO

                    from django.core.files.base import ContentFile
                    from PIL import Image

                    img = Image.open(self.cover)
                    try:
                        if img.mode != 'RGB':
                            img = img.convert('RGB')

                        MAX_SIZE = (800, 1200)
                        if img.height > MAX_SIZE[1] or img.width > MAX_SIZE[0]:
                            img.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)

                        buffer = BytesIO()
                        img.save(buffer, format='JPEG', quality=75, optimize=True)

                        filename = os.path.basename(self.cover.name)
                        # Use a unique name if necessary, but here we just want to avoid
                        # the infinite loop/duplicate issue on every model save
                        self.cover.save(filename, ContentFile(buffer.getvalue()), save=False)
                        buffer.close()
                    finally:
                        img.close()
            except Exception as e:
                logger.warning('Image optimization failed: %s', e)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-id']
        indexes = []


class BookIssue(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    issued_at = models.DateTimeField(auto_now_add=True, db_index=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    is_returned = models.BooleanField(default=False, db_index=True)
    return_qr_code = models.ImageField(upload_to='return_qrs/%Y/%m/%d/', null=True, blank=True)
    qr_token = models.CharField(max_length=255, null=True, blank=True)
    xp_awarded = models.BooleanField(default=False)
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        indexes = [
            models.Index(fields=['book', 'user']),
        ]

    def __str__(self):
        return f'{self.book.title} -> {self.user.username}'


class TextbookLoan(models.Model):
    CONDITION_CHOICES = (
        ('new', _('Yangi')),
        ('good', _('Yaxshi')),
        ('fair', _('Qoniqarli')),
        ('poor', _('Yomon')),
        ('lost', _("Yo'qolgan")),
    )
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, verbose_name=_('Kitob'), limit_choices_to={'is_textbook': True}
    )
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_("O'quvchi"))
    issued_at = models.DateField(_('Berilgan sana'), auto_now_add=True)
    due_date = models.DateField(_('Topshirish muddati'))
    returned_at = models.DateField(_('Qaytarilgan sana'), null=True, blank=True)
    condition_on_issue = models.CharField(
        _('Holati (berishda)'), max_length=10, choices=CONDITION_CHOICES, default='new'
    )
    condition_on_return = models.CharField(
        _('Holati (qaytarishda)'), max_length=10, choices=CONDITION_CHOICES, null=True, blank=True
    )
    notes = models.TextField(_('Izoh'), null=True, blank=True)
    academic_year = models.CharField(_("O'quv yili"), max_length=20, help_text='Masalan: 2025/2026')
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        verbose_name = _('Darslik ijarasi')
        verbose_name_plural = _('Darslik ijaralari')
        unique_together = [['book', 'student', 'academic_year']]

    def __str__(self):
        return f'{self.book.title} -> {self.student.username} ({self.academic_year})'


class BookRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', _('Kutilmoqda')),
        ('approved', _('Tasdiqlandi')),
        ('rejected', _('Rad etildi')),
        ('completed', _('Yakunlandi')),
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name=_('Kitob'), db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('Foydalanuvchi'), db_index=True
    )
    requested_at = models.DateTimeField(_("So'ralgan sana"), auto_now_add=True, db_index=True)
    status = models.CharField(_('Holati'), max_length=20, choices=STATUS_CHOICES, default='pending')
    qr_code = models.ImageField(upload_to='request_qrs/%Y/%m/%d/', null=True, blank=True)
    qr_token = models.CharField(max_length=255, null=True, blank=True)
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def __str__(self):
        return f'Request: {self.book.title} by {self.user.username}'


class BookWaitlist(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='waitlist', verbose_name=_('Kitob'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('Foydalanuvchi'))
    created_at = models.DateTimeField(_("Qo'shilgan sana"), auto_now_add=True)
    is_notified = models.BooleanField(_('Xabardor qilingan'), default=False)
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        ordering = ['created_at']
        unique_together = ['book', 'user']
        verbose_name = _('Navbatdagi kitob')
        verbose_name_plural = _('Navbatdagi kitoblar')

    def __str__(self):
        return f'{self.user.username} waits for {self.book.title}'


class Achievement(models.Model):
    key = models.CharField(_('Kalit'), max_length=50, unique=True)
    name = models.CharField(_('Nomi'), max_length=255)
    description = models.TextField(_('Tavsif'))
    icon = models.CharField(_('Ikonka'), max_length=50, default='fa-trophy')
    xp_reward = models.IntegerField(_('XP mukofoti'), default=25)
    condition_type = models.CharField(
        _('Shart turi'),
        max_length=50,
        choices=(
            ('books_count', _('Kitoblar soni')),
            ('categories', _('Kategoriyalar soni')),
            ('all_categories', _('Barcha kategoriyalar')),
            ('streak', _('Streak')),
            ('speed_return', _('Tez qaytarish')),
        ),
    )
    condition_value = models.IntegerField(_('Shart qiymati'))
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        ordering = ['name']
        verbose_name = _('Yutuq')
        verbose_name_plural = _('Yutuqlar')

    def __str__(self):
        return self.name


class UserAchievement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(_("Qo'lga kiritilgan vaqt"), auto_now_add=True)
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        unique_together = ['user', 'achievement']
        verbose_name = _("Foydalanuvchi yutug'i")
        verbose_name_plural = _('Foydalanuvchi yutuqlari')


class Challenge(models.Model):
    title = models.CharField(_('Sarlavha'), max_length=255)
    description = models.TextField(_('Tavsif'))
    challenge_type = models.CharField(
        _('Tur'),
        max_length=50,
        choices=(
            ('books_count', _('Kitoblar soni')),
            ('category', _('Kategoriya')),
        ),
    )
    target_count = models.IntegerField(_('Maqsad soni'))
    xp_reward = models.IntegerField(_('XP mukofoti'), default=50)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Kategoriya')
    )
    start_date = models.DateField(_('Boshlanish sanasi'))
    end_date = models.DateField(_('Tugash sanasi'))
    school = models.ForeignKey(
        'schools.School', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Maktab')
    )
    is_active = models.BooleanField(_('Faol'), default=True)
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        ordering = ['-start_date']
        verbose_name = _('Chellenj')
        verbose_name_plural = _('Chellenjlar')

    def __str__(self):
        return self.title


class UserChallenge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='challenges')
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    progress = models.IntegerField(_('Progress'), default=0)
    completed = models.BooleanField(_('Yakunlangan'), default=False)
    completed_at = models.DateTimeField(_('Yakunlangan vaqt'), null=True, blank=True)
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        unique_together = ['user', 'challenge']
        verbose_name = _('Foydalanuvchi chellenji')
        verbose_name_plural = _('Foydalanuvchi chellenjlari')

    def __str__(self):
        return f'{self.user.username} - {self.challenge.title} ({self.progress}/{self.challenge.target_count})'


class ReaderOfMonth(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('Foydalanuvchi'))
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, verbose_name=_('Maktab'))
    month = models.IntegerField(_('Oy'))
    year = models.IntegerField(_('Yil'))
    books_count = models.IntegerField(_('Kitoblar soni'))
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        unique_together = ['school', 'month', 'year']
        verbose_name = _("Oy o'quvchisi")
        verbose_name_plural = _("Oy o'quvchilari")

    def __str__(self):
        return f'{self.user.username} - {self.month}/{self.year} ({self.books_count} books)'


class BookCart(models.Model):
    STATUS_CHOICES = (
        ('pending', _('Kutilmoqda')),
        ('borrowed', _('Olingan')),
        ('returned', _('Qaytgan')),
    )
    PURPOSE_CHOICES = (
        ('borrow', _('Olish')),
        ('return', _('Qaytarish')),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('Foydalanuvchi'))
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, verbose_name=_('Maktab'))
    status = models.CharField(_('Holat'), max_length=20, choices=STATUS_CHOICES, default='pending')
    purpose = models.CharField(_('Maqsad'), max_length=10, choices=PURPOSE_CHOICES, default='borrow', db_index=True)
    qr_token = models.CharField(_('QR kod'), max_length=255, unique=True)
    created_at = models.DateTimeField(_('Yaratilgan vaqt'), auto_now_add=True)
    borrowed_at = models.DateTimeField(_('Olingan vaqt'), null=True, blank=True)
    returned_at = models.DateTimeField(_('Qaytgan vaqt'), null=True, blank=True)
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        verbose_name = _('Kitoblar savati')
        verbose_name_plural = _('Kitoblar savatlari')

    def __str__(self):
        return f'Savat #{self.id} - {self.user.username} - {self.status}'


class BookCartItem(models.Model):
    cart = models.ForeignKey(BookCart, on_delete=models.CASCADE, related_name='items', verbose_name=_('Savat'))
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name=_('Kitob'))
    created_at = models.DateTimeField(_("Qo'shilgan vaqt"), auto_now_add=True)
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        verbose_name = _('Savat kitobi')
        verbose_name_plural = _('Savat kitoblari')
        unique_together = ['cart', 'book']

    def __str__(self):
        return f'{self.cart.user.username}: {self.book.title}'
