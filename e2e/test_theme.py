import pytest

THEMES = ['dark', 'light', 'autumn', 'winter']
THEME_ICONS = ['fa-moon', 'fa-sun', 'fa-leaf', 'fa-snowflake']


@pytest.mark.e2e
@pytest.mark.parametrize('theme,icon', zip(THEMES, THEME_ICONS))
def test_theme_cycle(page, login, theme, icon):
    theme_btn = page.locator('#themeToggle')
    current = page.locator('html').get_attribute('data-theme') or 'dark'
    theme_index = THEMES.index(current)

    clicks_needed = (THEMES.index(theme) - theme_index) % len(THEMES)
    for _ in range(clicks_needed):
        theme_btn.click()
        page.wait_for_timeout(100)

    assert (page.locator('html').get_attribute('data-theme') or 'dark') == theme


@pytest.mark.e2e
def test_theme_cycles_all(page, login):
    theme_btn = page.locator('#themeToggle')
    start = page.locator('html').get_attribute('data-theme') or 'dark'
    start_index = THEMES.index(start)
    for i in range(4):
        current = page.locator('html').get_attribute('data-theme') or 'dark'
        assert current == THEMES[(start_index + i) % 4]
        theme_btn.click()
        page.wait_for_timeout(100)
