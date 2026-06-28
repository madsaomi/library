from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('superuser', _('Superuser')),
        ('school_admin', _('School Admin')),
        ('student', _('Student')),
        ('teacher', _('Teacher')),
    )
    role = models.CharField(_("Rol"), max_length=20, choices=ROLE_CHOICES, default='student')
    school = models.ForeignKey('schools.School', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Maktab"))
    grade = models.CharField(_("Sinf"), max_length=10, null=True, blank=True)
    subject = models.CharField(_("Fan"), max_length=100, null=True, blank=True)
    birth_date = models.DateField(_("Tug'ilgan sana"), null=True, blank=True)
    address = models.CharField(_("Yashash manzili"), max_length=255, null=True, blank=True)
    raw_password = models.CharField(_("Ochiq parol"), max_length=128, null=True, blank=True) # Foydalanuvchiga parolni ko'rsatish uchun

    def save(self, *args, **kwargs):
        if self.is_superuser and self.role != 'superuser':
            self.role = 'superuser'
        if self.role == 'superuser':
            self.is_superuser = True
            self.is_staff = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
