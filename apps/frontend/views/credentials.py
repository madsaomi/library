from django.http import HttpResponse
from django.utils import timezone


def download_credentials(request):
    """Download credentials as a simple text file."""
    username = request.GET.get('username', '')
    password = request.GET.get('password', '')
    full_name = request.GET.get('full_name', '')
    label = request.GET.get('label', 'Credentials')

    content = (
        f"Login: {username}\n"
        f"Password: {password}\n"
        f"Full Name: {full_name}\n"
        f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"Application: Online Kutibxona\n"
    )

    filename = f"credentials_{label.lower().replace(' ', '_')}_{timezone.now().strftime('%Y%m%d')}.txt"
    response = HttpResponse(content, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
