from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from books.models import Book
from accounts.models import CustomUser
from .models import News

def validate_word_limit(value, limit):
    if not value: return
    words = value.split()
    if len(words) > limit:
        raise ValidationError(_("Limit: %(limit)s ta so'z. Siz %(count)s ta so'z kiritdingiz.") % {'limit': limit, 'count': len(words)})

def validate_char_limit(value, limit):
    if not value: return
    if len(value) > limit:
        raise ValidationError(_("Limit: %(limit)s ta belgi. Siz %(count)s ta belgi kiritdingiz.") % {'limit': limit, 'count': len(value)})

class BookForm(forms.ModelForm):
    category_name = forms.CharField(
        required=False,
        label=_("Kategoriya"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'list': 'category-list', 'autocomplete': 'off'})
    )

    class Meta:
        model = Book
        fields = ['title', 'author', 'description', 'cover', 'total_count', 'available_count']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'data-limit-chars': '150', 'data-limit-words': '20'}),
            'author': forms.TextInput(attrs={'class': 'form-control', 'data-limit-chars': '150'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'data-limit-words': '500'}),
            'total_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'available_count': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from books.models import Category
        # Set initial value for category name if editing
        if self.instance and self.instance.category:
            self.fields['category_name'].initial = self.instance.category.name
        
        # Add categories for datalist
        self.categories = Category.objects.all().order_by('name')

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
        ('A', 'A'), ('B', 'B'), ('V', 'V'), ('G', 'G'), ('D', 'D'), 
        ('E', 'E'), ('F', 'F'), ('I', 'I'), ('J', 'J'), ('K', 'K'),
        ('L', 'L'), ('M', 'M'), ('N', 'N'), ('O', 'O'), ('P', 'P'),
        ('R', 'R'), ('S', 'S'), ('T', 'T'), ('U', 'U'), ('X', 'X')
    ]
    
    grade_number = forms.ChoiceField(
        choices=GRADE_NUMBERS, 
        label=_("Sinf"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    grade_letter = forms.ChoiceField(
        choices=GRADE_LETTERS, 
        label=_("Harf"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'birth_date']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'data-limit-chars': '50'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'data-limit-chars': '50'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _("Bo'sh qoldirilsa, avtomatik yaratiladi")}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.grade:
            # Try to split "7A" into "7" and "A"
            import re
            match = re.match(r"(\d+)([A-ZА-Я]?)", self.instance.grade)
            if match:
                self.fields['grade_number'].initial = match.group(1)
                self.fields['grade_letter'].initial = match.group(2)
        
        from django.utils.translation import gettext_lazy as _
        self.fields['first_name'].label = _("Ism")
        self.fields['last_name'].label = _("Familiya")
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
        user.grade = f"{num}{let}"
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
            'subject': forms.TextInput(attrs={'class': 'form-control', 'data-limit-chars': '100', 'list': 'subject-list', 'autocomplete': 'off'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("Yashash manzili")}),
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _("Bo'sh qoldirilsa, avtomatik yaratiladi")}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.utils.translation import gettext_lazy as _
        self.fields['first_name'].label = _("Ism")
        self.fields['last_name'].label = _("Familiya")
        self.fields['birth_date'].label = _("Tug'ilgan sana")
        self.fields['subject'].label = _("Fan")
        self.fields['address'].label = _("Yashash manzili")
        
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
            'title': forms.TextInput(attrs={'class': 'form-control', 'data-limit-chars': '150', 'data-limit-words': '20'}),
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
