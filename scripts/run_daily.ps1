# Run daily maintenance tasks
# Schedule in Windows Task Scheduler to run daily at a fixed time

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$Python = "python"
$Manage = Join-Path $ProjectDir "manage.py"

Write-Host "=== Daily tasks started: $(Get-Date) ==="

# 1. Check overdue loans and notify
& $Python $Manage check_overdue_loans

# 2. Cancel expired pending requests
& $Python $Manage cleanup_expired_requests

# 3. Update reading streaks
& $Python $Manage update_streaks

Write-Host "=== Daily tasks completed: $(Get-Date) ==="
