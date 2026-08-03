import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(username='admin', password='superadmin', email='')


@pytest.fixture
def live_server_url(live_server):
    return live_server.url


@pytest.fixture
def page(page):
    page.set_default_timeout(15000)
    return page


@pytest.fixture
def login(page, live_server_url):
    page.goto(live_server_url + '/login/')
    page.fill('#username', 'admin')
    page.fill('#password', 'superadmin')
    page.click('button[type="submit"]')
    page.wait_for_url('**/admin/**')
    return page
