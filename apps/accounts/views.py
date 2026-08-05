from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render


def login_view(request):
    if request.user.is_authenticated:
        return redirect_role_based(request.user)

    error = None
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            if (
                user.role == 'school_admin'
                and user.school is not None
                and (not user.school.is_active or user.school.is_deleted)
            ):
                from django.utils.translation import gettext as _

                error = _("Maktab faol emas yoki bloklangan. Administrator bilan bog'laning.")
            else:
                login(request, user)
                return redirect_role_based(user)
        else:
            from django.utils.translation import gettext as _

            error = _("Foydalanuvchi nomi yoki parol noto'g'ri")

    return render(request, 'login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('login')


def redirect_role_based(user):
    if user.role == 'superuser' or user.is_superuser:
        return redirect('frontend:dashboard')
    elif user.role == 'school_admin':
        return redirect('frontend:school_dashboard')
    else:
        return redirect('frontend:library')
