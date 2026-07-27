from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class PushSubscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='push_subscriptions',
        verbose_name=_('Foydalanuvchi'),
    )
    endpoint = models.URLField(max_length=500, verbose_name=_('Endpoint'))
    auth_key = models.CharField(max_length=100, verbose_name=_('Auth kalit'))
    p256dh_key = models.CharField(max_length=100, verbose_name=_('P256DH kalit'))
    created_at = models.DateTimeField(_('Yaratilgan sana'), auto_now_add=True)

    class Meta:
        verbose_name = _('Push obuna')
        verbose_name_plural = _('Push obunalar')

    def __str__(self):
        return f'Push: {self.user.username}'


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Foydalanuvchi'),
    )
    title = models.CharField(_('Sarlavha'), max_length=255)
    body = models.TextField(_('Matn'))
    url = models.CharField(_('Havola'), max_length=500, null=True, blank=True)
    is_read = models.BooleanField(_("O'qilgan"), default=False)
    created_at = models.DateTimeField(_('Yaratilgan sana'), auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Bildirishnoma')
        verbose_name_plural = _('Bildirishnomalar')

    def __str__(self):
        return f'[{self.user.username}] {self.title}'
