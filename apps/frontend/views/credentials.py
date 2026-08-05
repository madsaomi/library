from accounts.models import CustomUser
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext as _


@login_required(login_url='login')
def download_credentials(request):
    """Download credentials as a simple text file. Fetches password from DB by user id."""
    user_id = request.GET.get('user_id', '')
    label = request.GET.get('label', 'Foydalanuvchi')

    if not user_id or not user_id.isdigit():
        return HttpResponseForbidden(_("Noto'g'ri so'rov."))

    user = get_object_or_404(CustomUser, pk=int(user_id))

    # Only allow a superuser, or the school admin of the same school, to download
    if not (
        request.user.is_superuser or (request.user.role == 'school_admin' and user.school_id == request.user.school_id)
    ):
        return HttpResponseForbidden(_('Ruxsat berilmagan.'))

    password = user.raw_password or ''
    full_name = user.get_full_name() or user.username

    content = (
        f'Login: {user.username}\n'
        f'Password: {password}\n'
        f'Full Name: {full_name}\n'
        f'Generated: {timezone.now().strftime("%Y-%m-%d %H:%M")}\n'
        f'Application: Online Kutibxona\n'
    )

    safe_label = ''.join(c if c.isalnum() or c in ('_', '-') else '_' for c in label)
    filename = f'credentials_{safe_label.lower()}_{timezone.now().strftime("%Y%m%d")}.txt'
    response = HttpResponse(content, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
