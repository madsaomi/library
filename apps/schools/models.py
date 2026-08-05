from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class District(models.Model):
    name = models.CharField(_('Tuman nomi'), max_length=255, unique=True)
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Tuman')
        verbose_name_plural = _('Tumanlar')


class School(models.Model):
    name = models.CharField(_('Maktab nomi'), max_length=255, unique=True)
    address = models.CharField(_('Manzil'), max_length=255)
    contact = models.CharField(_('Kontakt'), max_length=255)
    district = models.ForeignKey(
        District, on_delete=models.SET_NULL, null=True, blank=True, related_name='schools', verbose_name=_('Tuman')
    )
    is_active = models.BooleanField(_('Faol'), default=True, help_text=_('Agar o\'chirilsa, maktab admini kira olmaydi'))
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)
    history = HistoricalRecords()

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = _('Maktab')
        verbose_name_plural = _('Maktablar')


class Institution(models.Model):
    name = models.CharField(_('Muassasa nomi'), max_length=255, unique=True)
    address = models.CharField(_('Manzil'), max_length=255)
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Muassasa')
        verbose_name_plural = _('Muassasalar')


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def __str__(self):
        return self.name


class GradePromotionLog(models.Model):
    promoted_at = models.DateTimeField(auto_now_add=True)
    year = models.IntegerField(unique=True)
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        db_table = 'frontend_school_gradepromotionlog'
        verbose_name = _("Sinf o'tkazish logi")
        verbose_name_plural = _("Sinf o'tkazish loglari")

    def __str__(self):
        return f'{self.year} - {self.promoted_at}'


class News(models.Model):
    school = models.ForeignKey(
        'schools.School', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Maktab')
    )
    title = models.CharField(_('Sarlavha'), max_length=255)
    body = models.TextField(_('Matn'))
    image = models.ImageField(_('Rasm'), upload_to='news_images/', null=True, blank=True)
    is_published = models.BooleanField(_('Nashr qilingan'), default=False)
    is_deleted = models.BooleanField(_("O'chirilgan"), default=False)
    created_at = models.DateTimeField(_('Yaratilgan sana'), auto_now_add=True, db_index=True)
    template_key = models.CharField(max_length=50, null=True, blank=True, editable=False)
    template_data = models.JSONField(null=True, blank=True, editable=False)

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        db_table = 'frontend_school_news'
        verbose_name = _('Yangilik')
        verbose_name_plural = _('Yangiliklar')

    def __str__(self):
        return self.title

    def render_body(self):
        if not self.template_key or not self.template_data:
            return self.body
        from django.utils.translation import gettext

        data = self.template_data
        if self.template_key == 'weekly_active':
            lines = []
            if data.get('schools'):
                lines.append(gettext('Eng faol maktablar'))
                for i, s in enumerate(data['schools'], 1):
                    lines.append(f'{i}. {s["name"]} — {s["count"]} {gettext("kitob berilgan")}')
            if data.get('readers'):
                lines.append('')
                lines.append(gettext('Eng faol kitobxonlar'))
                for i, r in enumerate(data['readers'], 1):
                    grade = f'({r["grade"]})' if r.get('grade') else ''
                    lines.append(f'{i}. {r["username"]} {grade} — {r["count"]} {gettext("kitob o'qigan")}')
            return '\n'.join(lines)
        if self.template_key == 'top_reader':
            s = data['student']
            lines = [
                gettext("Eng faol o'quvchi: {name}").format(name=s['name']),
                '',
                gettext("📚 Jami o'qilgan kitoblar: {books}").format(books=data.get('books', 0)),
                gettext('🔥 Haftalik streak: {streak} kun').format(streak=data.get('streak', 0)),
                gettext('⭐ Daraja: {level}').format(level=data.get('level', 1)),
                '',
                gettext(
                    "🏆 {school} jamoasi {name}ni tabriklaydi va barcha o'quvchilarni faol kitob o'qishga chorlaydi! 📖"
                ).format(school=s['school'], name=s['name']),
            ]
            return '\n'.join(lines)
        return self.body
