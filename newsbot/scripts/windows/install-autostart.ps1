# 부팅하면 로그인하지 않아도 자동으로 실행되게 등록 (관리자 권한 PowerShell에서 실행)
# 사용법: powershell -ExecutionPolicy Bypass -File scripts\windows\install-autostart.ps1
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { Write-Host "먼저 setup.ps1 을 실행하세요." -ForegroundColor Red; exit 1 }

$taskName = "ChungnyunBriefing"
$cred = Get-Credential -UserName "$env:USERDOMAIN\$env:USERNAME" -Message "로그인 없이 실행하려면 이 PC의 Windows 비밀번호가 필요합니다"

# 작업 폴더를 지정해야 상대 경로(.env, data)가 깨지지 않습니다 (기본값은 System32)
$action = New-ScheduledTaskAction -Execute $python -Argument "-m newsbot" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings `
    -User $cred.UserName -Password $cred.GetNetworkCredential().Password -RunLevel Limited -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Host "등록 완료: 부팅 때마다 자동 실행됩니다. 지금도 시작했습니다. (작업 스케줄러 > $taskName)" -ForegroundColor Green
