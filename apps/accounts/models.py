from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('superuser', _('Superuser')),
        ('school_admin', _('School Admin')),
        ('student', _('Student')),
        ('teacher', _('Teacher')),
    )
    role = models.CharField(_('Rol'), max_length=20, choices=ROLE_CHOICES, default='student', db_index=True)
    school = models.ForeignKey(
        'schools.School', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Maktab')
    )
    grade = models.CharField(_('Sinf'), max_length=10, null=True, blank=True)
    subject = models.CharField(_('Fan'), max_length=100, null=True, blank=True)
    birth_date = models.DateField(_("Tug'ilgan sana"), null=True, blank=True)
    address = models.CharField(_('Yashash manzili'), max_length=255, null=True, blank=True)
    raw_password = models.CharField(_('Ochiq parol'), max_length=128, null=True, blank=True)
    is_archived = models.BooleanField(_('Arxivlangan'), default=False)
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)

    # Gamification fields
    xp_points = models.IntegerField(_('XP ball'), default=0)
    level = models.IntegerField(_('Daraja'), default=1)
    current_streak = models.IntegerField(_('Joriy streak'), default=0)
    longest_streak = models.IntegerField(_('Eng uzun streak'), default=0)
    last_activity_date = models.DateField(_('Oxirgi faollik'), null=True, blank=True)
    total_books_read = models.IntegerField(_("O'qilgan kitoblar"), default=0)
    monthly_books_read = models.IntegerField(_('Oylik kitoblar'), default=0)
    selected_icon = models.CharField(_('Tanlangan ikonka'), max_length=50, default='fa-book')
    unlocked_icons = models.JSONField(_('Ochiq ikonkalar'), default=list)

    objects = UserManager()
    active_objects = SoftDeleteManager()
    history = HistoricalRecords(excluded_fields=['raw_password'])

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def save(self, *args, **kwargs):
        if self.is_superuser and self.role != 'superuser':
            self.role = 'superuser'
        if self.role == 'superuser':
            self.is_superuser = True
            self.is_staff = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'
