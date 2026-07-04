# Run weekly maintenance tasks
# Schedule in Windows Task Scheduler to run weekly (e.g. every Monday)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$Python = "python"
$Manage = Join-Path $ProjectDir "manage.py"

Write-Host "=== Weekly tasks started: $(Get-Date) ==="

# 1. Create weekly active schools/readers news
& $Python $Manage create_weekly_news --days 7

Write-Host "=== Weekly tasks completed: $(Get-Date) ==="
