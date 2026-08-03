import pytest


@pytest.mark.e2e
def test_login_page_loads(page, live_server_url):
    page.goto(live_server_url + '/login/')
    assert page.title() != ''
    assert page.is_visible('#username')
    assert page.is_visible('#password')


@pytest.mark.e2e
def test_login_success(page, live_server_url):
    page.goto(live_server_url + '/login/')
    page.fill('#username', 'admin')
    page.fill('#password', 'superadmin')
    page.click('button[type="submit"]')
    page.wait_for_url('**/admin/**')
    assert '/admin/' in page.url


@pytest.mark.e2e
def test_login_failure(page, live_server_url):
    page.goto(live_server_url + '/login/')
    page.fill('#username', 'admin')
    page.fill('#password', 'wrongpassword')
    page.click('button[type="submit"]')
    assert '/login/' in page.url or page.is_visible('.error')


@pytest.mark.e2e
def test_logout(page, login, live_server_url):
    page.goto(live_server_url + '/')
    page.click('a[href*="logout"]')
    page.wait_for_url('**/login/**')
    assert '/login/' in page.url
