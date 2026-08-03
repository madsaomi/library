import pytest


@pytest.mark.e2e
def test_dashboard_loads(page, login, live_server_url):
    page.goto(live_server_url + '/admin/')
    assert page.is_visible('.main-content')
    assert 'dashboard' in page.content().lower()


@pytest.mark.e2e
def test_sidebar_visible(page, login):
    sidebar = page.locator('#sidebar')
    assert sidebar.is_visible()


@pytest.mark.e2e
def test_profile_link(page, login, live_server_url):
    page.goto(live_server_url + '/')
    profile_link = page.locator('a[href*="profile"]').first
    if profile_link.is_visible():
        profile_link.click()
        page.wait_for_timeout(500)
        assert 'profile' in page.url


@pytest.mark.e2e
def test_notification_panel(page, login):
    bell = page.locator('#notificationBell')
    bell.click()
    page.wait_for_timeout(300)
    panel = page.locator('#notificationPanel')
    assert panel.is_visible()
    bell.click()
    page.wait_for_timeout(300)
    assert not panel.is_visible()


@pytest.mark.e2e
def test_language_switch(page, login):
    lang_btn = page.locator('.language-selector')
    if lang_btn.is_visible():
        lang_btn.click()
        page.wait_for_timeout(200)
        options = page.locator('.lang-option')
        count = options.count()
        assert count >= 2
