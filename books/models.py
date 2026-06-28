from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class Category(models.Model):
    name = models.CharField(_("Nomi"), max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Kategoriya")
        verbose_name_plural = _("Kategoriyalar")

class Book(models.Model):
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, verbose_name=_("Maktab"))
    title = models.CharField(_("Sarlavha"), max_length=255)
    author = models.CharField(_("Muallif"), max_length=255, null=True, blank=True)
    description = models.TextField(_("Tavsif"))
    cover = models.ImageField(_("Muqova"), upload_to='book_covers/%Y/%m/%d/', null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Kategoriya"))
    total_count = models.IntegerField(_("Umumiy soni"))
    available_count = models.IntegerField(_("Mavjud soni"))
    borrow_count = models.IntegerField(_("O'qilganlar soni"), default=0)


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
                    from PIL import Image
                    from io import BytesIO
                    from django.core.files.base import ContentFile
                    import os

                    img = Image.open(self.cover)
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
            except Exception as e:
                print(f"Error optimizing image: {e}")
                
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class BookIssue(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    issued_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    is_returned = models.BooleanField(default=False)
    return_qr_code = models.ImageField(upload_to='return_qrs/%Y/%m/%d/', null=True, blank=True)
    qr_token = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.book.title} -> {self.user.username}"

class BookRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', _('Kutilmoqda')),
        ('approved', _('Tasdiqlandi')),
        ('rejected', _('Rad etildi')),
        ('completed', _('Yakunlandi')),
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name=_("Kitob"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_("Foydalanuvchi"))
    requested_at = models.DateTimeField(_("So'ralgan sana"), auto_now_add=True)
    status = models.CharField(_("Holati"), max_length=20, choices=STATUS_CHOICES, default='pending')
    qr_code = models.ImageField(upload_to='request_qrs/%Y/%m/%d/', null=True, blank=True)
    qr_token = models.CharField(max_length=255, null=True, blank=True)


    def __str__(self):
        return f"Request: {self.book.title} by {self.user.username}"


class BookWaitlist(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='waitlist', verbose_name=_("Kitob"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_("Foydalanuvchi"))
    created_at = models.DateTimeField(_("Qo'shilgan sana"), auto_now_add=True)
    is_notified = models.BooleanField(_("Xabardor qilingan"), default=False)

    class Meta:
        ordering = ['created_at']
        unique_together = ['book', 'user']
        verbose_name = _("Navbatdagi kitob")
        verbose_name_plural = _("Navbatdagi kitoblar")

    def __str__(self):
        return f"{self.user.username} waits for {self.book.title}"
