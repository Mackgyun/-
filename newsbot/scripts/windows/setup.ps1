# 청년의사 브리핑 설치 (한 번만 실행)
# 사용법: newsbot 폴더에서 PowerShell을 열고  powershell -ExecutionPolicy Bypass -File scripts\windows\setup.ps1
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Host "Python이 없습니다. https://www.python.org/downloads/ 에서 3.11 이상을 설치하고 'Add python.exe to PATH'를 체크한 뒤 다시 실행하세요." -ForegroundColor Red
    exit 1
}
py -3 -c "import sys; assert sys.version_info >= (3, 11), sys.version" 
if ($LASTEXITCODE -ne 0) { Write-Host "Python 3.11 이상이 필요합니다." -ForegroundColor Red; exit 1 }

if (-not (Test-Path ".venv")) { py -3 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env 파일을 만들었습니다. 메모장으로 열어 DART_API_KEY 를 넣어 주세요." -ForegroundColor Yellow
}
New-Item -ItemType Directory -Force -Path "data" | Out-Null

Write-Host ""
Write-Host "설치 완료. 다음 순서로 진행하세요:" -ForegroundColor Green
Write-Host "  1) 관리자 계정:  .\.venv\Scripts\python.exe -m newsbot create-admin 내아이디 --name 내이름"
Write-Host "  2) 실행:         scripts\windows\start.bat"
Write-Host "  3) 브라우저:     http://localhost:8000"
