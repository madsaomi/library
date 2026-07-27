from accounts.models import CustomUser
from books.models import Book
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.validators import validate_char_limit, validate_word_limit

SUBJECT_CHOICES = [
    ('', '---'),
    ('Matematika', _('Matematika')),
    ('Fizika', _('Fizika')),
    ('Kimyo', _('Kimyo')),
    ('Biologiya', _('Biologiya')),
    ('Informatika', _('Informatika')),
    ('Tarix', _('Tarix')),
    ('Geografiya', _('Geografiya')),
    ("O'zbek tili", _("O'zbek tili")),
    ('Adabiyot', _('Adabiyot')),
    ('Ingliz tili', _('Ingliz tili')),
    ('Rus tili', _('Rus tili')),
    ('Jismoniy tarbiya', _('Jismoniy tarbiya')),
    ('Huquq', _('Huquq')),
    ('Iqtisod', _('Iqtisod')),
]
from schools.models import News


class BookForm(forms.ModelForm):
    category_name = forms.CharField(
        required=False,
        label=_('Kategoriya'),
        widget=forms.TextInput(attrs={'class': 'form-control', 'list': 'category-list', 'autocomplete': 'off'}),
    )

    class Meta:
        model = Book
        fields = [
            'title',
            'author',
            'description',
            'cover',
            'total_count',
            'available_count',
            'is_textbook',
            'subject',
            'grade',
        ]
        widgets = {
            'title': forms.TextInput(
                attrs={'class': 'form-control', 'data-limit-chars': '150', 'data-limit-words': '20'}
            ),
            'author': forms.TextInput(attrs={'class': 'form-control', 'data-limit-chars': '150'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'data-limit-words': '500'}),
            'total_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'available_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_textbook': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'list': 'subject-list', 'autocomplete': 'off'}),
            'grade': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 11}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from books.models import Category

        # Set initial value for category name if editing
        if self.instance and self.instance.category:
            self.fields['category_name'].initial = self.instance.category.name

        # Add categories for datalist
        self.categories = Category.objects.all().order_by('name')

        # Pass subject list for datalist
        self.subject_choices = [c[0] for c in SUBJECT_CHOICES if c[0]]

    def clean_title(self):
        title = self.cleaned_data.get('title')
        validate_char_limit(title, 150)
        validate_word_limit(title, 20)
        return title

    def clean_description(self):
        desc = self.cleaned_data.get('description')
        validate_word_limit(desc, 500)
        return desc

    def save(self, commit=True):
        from books.models import Category

        category_name = self.cleaned_data.get('category_name')
        book = super().save(commit=False)

        if category_name:
            category, created = Category.objects.get_or_create(name=category_name)
            book.category = category
        else:
            book.category = None

        if commit:
            book.save()
        return book


class StudentForm(forms.ModelForm):
    GRADE_NUMBERS = [(str(i), str(i)) for i in range(1, 12)]
    GRADE_LETTERS = [
        ('A', 'A'),
        ('B', 'B'),
        ('V', 'V'),
        ('G', 'G'),
        ('D', 'D'),
        ('E', 'E'),
        ('F', 'F'),
        ('I', 'I'),
        ('J', 'J'),
        ('K', 'K'),
        ('L', 'L'),
        ('M', 'M'),
        ('N', 'N'),
        ('O', 'O'),
        ('P', 'P'),
        ('R', 'R'),
        ('S', 'S'),
        ('T', 'T'),
        ('U', 'U'),
        ('X', 'X'),
    ]

    grade_number = forms.ChoiceField(
        choices=GRADE_NUMBERS, label=_('Sinf'), widget=forms.Select(attrs={'class': 'form-control'})
    )
    grade_letter = forms.ChoiceField(
        choices=GRADE_LETTERS, label=_('Harf'), widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'birth_date']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'data-limit-chars': '50'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'data-limit-chars': '50'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'password': forms.PasswordInput(
                attrs={'class': 'form-control', 'placeholder': _("Bo'sh qoldirilsa, avtomatik yaratiladi")}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.grade:
            # Try to split "7A" into "7" and "A"
            import re

            match = re.match(r'(\d+)([A-ZА-Я]?)', self.instance.grade)
            if match:
                self.fields['grade_number'].initial = match.group(1)
                self.fields['grade_letter'].initial = match.group(2)

        from django.utils.translation import gettext_lazy as _

        self.fields['first_name'].label = _('Ism')
        self.fields['last_name'].label = _('Familiya')
        self.fields['birth_date'].label = _("Tug'ilgan sana")
        self.fields['birth_date'].required = True

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date:
            from datetime import date

            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            if age < 7:
                raise ValidationError(_("O'quvchi kamida 7 yosh bo'lishi kerak!"))
        return birth_date

    def clean_first_name(self):
        name = self.cleaned_data.get('first_name')
        validate_char_limit(name, 50)
        return name

    def clean_last_name(self):
        name = self.cleaned_data.get('last_name')
        validate_char_limit(name, 50)
        return name

    def save(self, commit=True):
        user = super().save(commit=False)
        num = self.cleaned_data.get('grade_number')
        let = self.cleaned_data.get('grade_letter')
        user.grade = f'{num}{let}'
        if commit:
            user.save()
        return user


class TeacherForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'birth_date', 'subject', 'address']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'data-limit-chars': '50'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'data-limit-chars': '50'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'subject': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'data-limit-chars': '100',
                    'list': 'subject-list',
                    'autocomplete': 'off',
                }
            ),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Yashash manzili')}),
            'password': forms.PasswordInput(
                attrs={'class': 'form-control', 'placeholder': _("Bo'sh qoldirilsa, avtomatik yaratiladi")}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.utils.translation import gettext_lazy as _

        self.fields['first_name'].label = _('Ism')
        self.fields['last_name'].label = _('Familiya')
        self.fields['birth_date'].label = _("Tug'ilgan sana")
        self.fields['subject'].label = _('Fan')
        self.fields['address'].label = _('Yashash manzili')

        from schools.models import Subject

        self.subjects = Subject.objects.all().order_by('name')

    def clean_first_name(self):
        name = self.cleaned_data.get('first_name')
        validate_char_limit(name, 50)
        return name

    def clean_last_name(self):
        name = self.cleaned_data.get('last_name')
        validate_char_limit(name, 50)
        return name

    def clean_username(self):
        name = self.cleaned_data.get('username')
        validate_char_limit(name, 50)
        return name

    def clean_subject(self):
        val = self.cleaned_data.get('subject')
        validate_char_limit(val, 100)
        return val


class NewsForm(forms.ModelForm):
    class Meta:
        model = News
        fields = ['title', 'body', 'image', 'is_published']
        widgets = {
            'title': forms.TextInput(
                attrs={'class': 'form-control', 'data-limit-chars': '150', 'data-limit-words': '20'}
            ),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'data-limit-words': '1000'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title')
        validate_char_limit(title, 150)
        validate_word_limit(title, 20)
        return title

    def clean_body(self):
        body = self.cleaned_data.get('body')
        validate_word_limit(body, 1000)
        return body


from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _
from schools.models import District, Institution, School


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
        label=_('Avtomatik maktablar yaratish'),
        help_text=_("Ushbu tumanga avtomatik tarzda n-ta maktab qo'shish uchun raqam kiriting."),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('Masalan: 10')}),
    )

    class Meta:
        model = District
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
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


SchoolFormSet = inlineformset_factory(District, School, form=SchoolInlineForm, extra=1, can_delete=True)


class InstitutionForm(forms.ModelForm):
    class Meta:
        model = Institution
        fields = ['name', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_name(self):
        val = self.cleaned_data.get('name')
        validate_char_limit(val, 150)
        return val


from accounts.models import CustomUser


class SchoolAdminForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text=_("Yangi foydalanuvchi uchun majburiy. Tahrirlashda bo'sh qoldirsa o'zgarmaydi."),
    )
    admin_username = forms.CharField(
        label=_('Admin login (username)'),
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'username', 'autocomplete': 'new-username'}
        ),
    )
    admin_password = forms.CharField(
        label=_('Admin paroli'),
        required=False,
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': '********', 'autocomplete': 'new-password'}
        ),
    )
    admin_password_confirm = forms.CharField(
        label=_('Parolni tasdiqlash'),
        required=False,
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': '********', 'autocomplete': 'new-password'}
        ),
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'school']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'family-name'}),
            'school': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_first_name(self):
        val = self.cleaned_data.get('first_name')
        validate_char_limit(val, 50)
        return val

    def clean_last_name(self):
        val = self.cleaned_data.get('last_name')
        validate_char_limit(val, 50)
        return val

    def clean(self):
        cleaned_data = super().clean()
        admin_username = cleaned_data.get('admin_username')
        admin_password = cleaned_data.get('admin_password')
        admin_password_confirm = cleaned_data.get('admin_password_confirm')

        if admin_username or admin_password or admin_password_confirm:
            if not admin_username:
                self.add_error('admin_username', _('Login kiriting'))
            if not admin_password:
                self.add_error('admin_password', _('Parol kiriting'))
            if admin_password != admin_password_confirm:
                self.add_error('admin_password_confirm', _('Parollar mos kelmadi.'))

            if (
                admin_username
                and CustomUser.objects.filter(username=admin_username)
                .exclude(pk=self.instance.pk if self.instance.pk else None)
                .exists()
            ):
                self.add_error('admin_username', _('Ushbu login band!'))

        return cleaned_data


class UnifiedSchoolForm(forms.ModelForm):
    existing_school_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    admin_username = forms.CharField(
        label=_('Admin login (username)'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'username'}),
    )
    admin_password = forms.CharField(
        label=_('Admin paroli'),
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '********'}),
    )
    admin_password_confirm = forms.CharField(
        label=_('Parolni tasdiqlash'),
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '********'}),
    )

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
                self.add_error('admin_username', _('Login kiriting'))
            if not admin_password:
                self.add_error('admin_password', _('Parol kiriting'))
            if admin_password != admin_password_confirm:
                self.add_error('admin_password_confirm', _('Parollar mos kelmadi.'))

            if CustomUser.objects.filter(username=admin_username).exclude(pk=self.current_admin_id).exists():
                self.add_error('admin_username', _('Ushbu login band!'))

        # Extra check: if we are in "Add" mode but existing_school_id is set,
        # ensure we are treating it as an update for the school model
        existing_id = cleaned_data.get('existing_school_id')
        if existing_id and not self.instance.pk:
            # This case should be handled by passing instance in the view,
            # but this is a safety net.
            pass

        return cleaned_data
