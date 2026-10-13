<#
.SYNOPSIS
    Installs, starts, or removes the Ultra Core Watchdog as a Windows Scheduled Task.

.DESCRIPTION
    Ensures scripts/watchdog.py runs continuously in the background on boot/logon.
    Usage:
        powershell -ExecutionPolicy Bypass -File scripts/ultra_core_watchdog_service.ps1 -Action Install
        powershell -ExecutionPolicy Bypass -File scripts/ultra_core_watchdog_service.ps1 -Action Start
        powershell -ExecutionPolicy Bypass -File scripts/ultra_core_watchdog_service.ps1 -Action Status
        powershell -ExecutionPolicy Bypass -File scripts/ultra_core_watchdog_service.ps1 -Action Uninstall
#>

param (
    [ValidateSet("Install", "Start", "Stop", "Status", "Uninstall")]
    [string]$Action = "Status"
)

$TaskName = "UltraCoreWatchdog"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PythonExe = Join-Path $RepoRoot "venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
}

if (-not $PythonExe) {
    Write-Error "Python executable not found. Please activate your venv or ensure python is in PATH."
    exit 1
}

$ScriptPath = Join-Path $RepoRoot "scripts\watchdog.py"

switch ($Action) {
    "Install" {
        Write-Host "Registering Windows Scheduled Task: $TaskName ..." -ForegroundColor Cyan
        $ActionCmd = New-ScheduledTaskAction -Execute $PythonExe -Argument "-u $ScriptPath" -WorkingDirectory $RepoRoot
        $Trigger = New-ScheduledTaskTrigger -AtLogOn
        $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 365)
        
        Register-ScheduledTask -TaskName $TaskName -Action $ActionCmd -Trigger $Trigger -Settings $Settings -Description "Ultra Core Watchdog keepalive monitor" -Force
        Write-Host "Task '$TaskName' registered successfully." -ForegroundColor Green
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "Task '$TaskName' started." -ForegroundColor Green
    }
    "Start" {
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "Task '$TaskName' started." -ForegroundColor Green
    }
    "Stop" {
        Stop-ScheduledTask -TaskName $TaskName
        Write-Host "Task '$TaskName' stopped." -ForegroundColor Yellow
    }
    "Status" {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($task) {
            $info = Get-ScheduledTaskInfo -TaskName $TaskName
            Write-Host "Task: $($task.TaskName) | State: $($task.State)" -ForegroundColor Cyan
            Write-Host "Last Run: $($info.LastRunTime) | Last Result: $($info.LastTaskResult)"
        } else {
            Write-Host "Task '$TaskName' is not installed." -ForegroundColor Yellow
        }
    }
    "Uninstall" {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "Task '$TaskName' unregistered." -ForegroundColor Green
    }
}
