# 촬영원본 동기화를 Windows 작업 스케줄러에 등록합니다.
# 관리자 PowerShell에서 실행:  powershell -ExecutionPolicy Bypass -File register_task.ps1

param(
    [int]$IntervalMinutes = 15,
    [string]$TaskName = "촬영원본-구글시트-동기화"
)

$here = Split-Path -Parent $MyInvocation.MyCommand.Definition
$bat  = Join-Path $here "run_sync.bat"

if (-not (Test-Path $bat)) { throw "run_sync.bat 을 찾을 수 없습니다: $bat" }

$action    = New-ScheduledTaskAction -Execute $bat -WorkingDirectory $here
$trigger   = New-ScheduledTaskTrigger -Once -At (Get-Date) `
                -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable `
                -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "NAS 촬영원본 폴더를 구글 시트에 반영" -Force

Write-Host "등록 완료: '$TaskName' ($IntervalMinutes분마다 실행)"
Write-Host "확인:  Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "즉시 실행:  Start-ScheduledTask -TaskName '$TaskName'"
