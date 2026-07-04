# Run monthly maintenance tasks
# Schedule in Windows Task Scheduler to run monthly (e.g. 1st of each month)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$Python = "python"
$Manage = Join-Path $ProjectDir "manage.py"

Write-Host "=== Monthly tasks started: $(Get-Date) ==="

# 1. Assign Reader of the Month + create news
& $Python $Manage assign_monthly_reader

# 2. Clean up old logs, notifications, sessions
& $Python $Manage cleanup_old_data

Write-Host "=== Monthly tasks completed: $(Get-Date) ==="
