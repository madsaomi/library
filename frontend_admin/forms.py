from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from schools.models import School, Institution, District

def validate_word_limit(value, limit):
    if not value: return
    words = value.split()
    if len(words) > limit:
        raise ValidationError(_("Limit: %(limit)s ta so'z. Siz %(count)s ta so'z kiritdingiz.") % {'limit': limit, 'count': len(words)})

def validate_char_limit(value, limit):
    if not value: return
    if len(value) > limit:
        raise ValidationError(_("Limit: %(limit)s ta belgi. Siz %(count)s ta belgi kiritdingiz.") % {'limit': limit, 'count': len(value)})

class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ['district', 'name', 'address', 'contact']
        widgets = {
            'district': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'data-limit-chars': '150'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'data-limit-chars': '255'}),
            'contact': forms.TextInput(attrs={'class': 'form-control', 'data-limit-chars': '100'}),
        }
    def clean_name(self):
        name = self.cleaned_data.get('name')
        validate_char_limit(name, 150)
        return name
    def clean_address(self):
        val = self.cleaned_data.get('address')
        validate_char_limit(val, 255)
        return val
        
class DistrictForm(forms.ModelForm):
    bulk_schools_count = forms.IntegerField(
        required=False, 
        min_value=1, 
        max_value=100,
        label=_("Avtomatik maktablar yaratish"),
        help_text=_("Ushbu tumanga avtomatik tarzda n-ta maktab qo'shish uchun raqam kiriting."),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('Masalan: 10')})
    )

    class Meta:
        model = District
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'data-limit-chars': '100'}),
        }
    def clean_name(self):
        val = self.cleaned_data.get('name')
        validate_char_limit(val, 100)
        return val

class SchoolInlineForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ['name', 'address', 'contact']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Maktab nomi'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Manzil'}),
            'contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Aloqa'}),
        }

SchoolFormSet = inlineformset_factory(
    District, 
    School, 
    form=SchoolInlineForm,
    extra=1, 
    can_delete=True
)
class InstitutionForm(forms.ModelForm):
    class Meta:
        model = Institution
        fields = ['name', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'data-limit-chars': '150'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'data-limit-chars': '255'}),
        }
    def clean_name(self):
        val = self.cleaned_data.get('name')
        validate_char_limit(val, 150)
        return val

from accounts.models import CustomUser

class SchoolAdminForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False, help_text=_("Yangi foydalanuvchi uchun majburiy. Tahrirlashda bo'sh qoldirsa o'zgarmaydi."))
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'school']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'school': forms.Select(attrs={'class': 'form-control'}),
        }
    def clean_username(self):
        val = self.cleaned_data.get('username')
        validate_char_limit(val, 50)
        return val
    def clean_first_name(self):
        val = self.cleaned_data.get('first_name')
        validate_char_limit(val, 50)
        return val
    def clean_last_name(self):
        val = self.cleaned_data.get('last_name')
        validate_char_limit(val, 50)
        return val

class UnifiedSchoolForm(forms.ModelForm):
    existing_school_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    admin_username = forms.CharField(label=_("Admin login (username)"), required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'username'}))
    admin_password = forms.CharField(label=_("Admin paroli"), required=False, widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '********'}))
    admin_password_confirm = forms.CharField(label=_("Parolni tasdiqlash"), required=False, widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '********'}))

    class Meta:
        model = School
        fields = ['district', 'name', 'address', 'contact']
        widgets = {
            'district': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'contact': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    field_order = ['district', 'name', 'address', 'contact', 'existing_school_id']

    def __init__(self, *args, **kwargs):
        self.current_admin_id = kwargs.pop('current_admin_id', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        admin_username = cleaned_data.get('admin_username')
        admin_password = cleaned_data.get('admin_password')
        admin_password_confirm = cleaned_data.get('admin_password_confirm')

        # Check if we are creating a NEW admin
        # In school_add instance.pk is None. In school_edit, we check if school already has an admin in the view, 
        # but here we just check if any admin field is filled.
        
        if admin_username or admin_password or admin_password_confirm:
            if not admin_username:
                self.add_error('admin_username', _("Login kiriting."))
            if not admin_password:
                self.add_error('admin_password', _("Parol kiriting."))
            if admin_password != admin_password_confirm:
                self.add_error('admin_password_confirm', _("Parollar mos kelmadi."))
            
            if CustomUser.objects.filter(username=admin_username).exclude(pk=self.current_admin_id).exists():
                self.add_error('admin_username', _("Ushbu login band. Boshqa tanlang."))

        # Extra check: if we are in "Add" mode but existing_school_id is set,
        # ensure we are treating it as an update for the school model
        existing_id = cleaned_data.get('existing_school_id')
        if existing_id and not self.instance.pk:
            # This case should be handled by passing instance in the view, 
            # but this is a safety net.
            pass

        return cleaned_data
