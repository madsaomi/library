from django.db import models
from django.utils.translation import gettext_lazy as _

class District(models.Model):
    name = models.CharField(_("Tuman nomi"), max_length=255, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Tuman")
        verbose_name_plural = _("Tumanlar")

class School(models.Model):
    name = models.CharField(_("Maktab nomi"), max_length=255, unique=True)
    address = models.CharField(_("Manzil"), max_length=255)
    contact = models.CharField(_("Kontakt"), max_length=255)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True, related_name='schools', verbose_name=_("Tuman"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Maktab")
        verbose_name_plural = _("Maktablar")


class Institution(models.Model):
    name = models.CharField(_("Muassasa nomi"), max_length=255, unique=True)
    address = models.CharField(_("Manzil"), max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Muassasa")
        verbose_name_plural = _("Muassasalar")


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
