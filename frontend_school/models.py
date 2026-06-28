from django.db import models
from django.utils.translation import gettext_lazy as _

class News(models.Model):
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("Maktab"))
    title = models.CharField(_("Sarlavha"), max_length=255)
    body = models.TextField(_("Matn"))
    image = models.ImageField(_("Rasm"), upload_to='news_images/', null=True, blank=True)
    is_published = models.BooleanField(_("Nashr qilingan"), default=False)
    created_at = models.DateTimeField(_("Yaratilgan sana"), auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _("Yangilik")
        verbose_name_plural = _("Yangiliklar")

