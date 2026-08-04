from django.contrib.auth.decorators import login_required


@login_required(login_url='login')
def profile(request):
    if request.user.is_superuser:
        from .admin_views import profile as admin_profile

        return admin_profile(request)
    if request.user.role == 'school_admin':
        from .school_views import profile as school_profile

        return school_profile(request)
    from .user_views import profile as user_profile

    return user_profile(request)


@login_required(login_url='login')
def change_password(request):
    if request.user.is_superuser:
        from .admin_views import change_password as admin_change_password

        return admin_change_password(request)
    if request.user.role == 'school_admin':
        from .school_views import change_password as school_change_password

        return school_change_password(request)
    from .user_views import change_password as user_change_password

    return user_change_password(request)
