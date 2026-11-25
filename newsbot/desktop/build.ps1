# 청년의사 브리핑 PC 알림 프로그램을 exe 한 파일로 만든다.
#   powershell -ExecutionPolicy Bypass -File desktop\build.ps1
# 결과: desktop\dist\청년의사브리핑알림.exe
# 편집국에 배포할 때는 같은 폴더에 server.txt (예: https://briefing.도메인) 를 두면 로그인 창의 기본 주소가 된다.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}
.\.venv\Scripts\python.exe -m pip install -q --disable-pip-version-check -r requirements.txt
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name "청년의사브리핑알림" --icon "$here\assets\icon.ico" `
    --add-data "$here\assets;assets" `
    --collect-submodules windows_toasts --collect-submodules winrt `
    --distpath dist --workpath build --specpath build "$here\notifier.py"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller 실패" }
Write-Host "완료: $here\dist\청년의사브리핑알림.exe"
