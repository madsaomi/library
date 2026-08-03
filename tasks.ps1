param(
    [string]$Command = "help"
)

$PYTHON = "python"
$DJANGO = "$PYTHON manage.py"

switch ($Command) {
    "help" {
        Write-Host "Usage: .\tasks.ps1 <command>" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Commands:" -ForegroundColor Yellow
        Write-Host "  install      Install dependencies"
        Write-Host "  lint         Run ruff linter"
        Write-Host "  format       Run ruff formatter"
        Write-Host "  test         Run pytest"
        Write-Host "  migrate      Run Django migrations"
        Write-Host "  seed         Seed test users"
        Write-Host "  runserver    Start dev server"
        Write-Host "  static       Collect static files"
        Write-Host "  setup        Full project setup"
        Write-Host "  clean        Remove cache files"
    }
    "install" {
        & $PYTHON -m pip install -r requirements-dev.txt
        & $PYTHON -m playwright install chromium
    }
    "lint" {
        & $PYTHON -m ruff check .
    }
    "format" {
        & $PYTHON -m ruff format .
    }
    "format-check" {
        & $PYTHON -m ruff format --check .
    }
    "test" {
        $env:SECRET_KEY = "test"; $env:DEBUG = "True"
        & $PYTHON -m pytest -q --tb=short
    }
    "migrate" {
        & $DJANGO migrate
    }
    "seed" {
        $env:SECRET_KEY = "test-key-not-for-production"; $env:DEBUG = "True"
        & $DJANGO seed_test_users
    }
    "runserver" {
        $env:SECRET_KEY = "test-key-not-for-production"; $env:DEBUG = "True"
        & $DJANGO runserver 8000
    }
    "static" {
        & $DJANGO collectstatic --noinput --clear
    }
    "setup" {
        .\tasks.ps1 install
        .\tasks.ps1 migrate
        .\tasks.ps1 seed
        .\tasks.ps1 static
        .\tasks.ps1 runserver
    }
    "clean" {
        Get-ChildItem -Recurse -Include "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
        Get-ChildItem -Recurse -Include "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force
        Remove-Item -Recurse -Force ".ruff_cache", ".pytest_cache" -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force "staticfiles" -ErrorAction SilentlyContinue
        Write-Host "Cleaned." -ForegroundColor Green
    }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host "Run .\tasks.ps1 help for available commands."
    }
}
