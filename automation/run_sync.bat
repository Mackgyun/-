@echo off
chcp 65001 > nul
REM 촬영원본 -> 구글시트 동기화 (작업 스케줄러에서 이 파일을 실행하세요)
cd /d "%~dp0"

REM NAS에 로그인이 필요한 경우 아래 줄의 REM을 지우고 계정을 채우세요.
REM net use \\192.168.0.45\10tb /user:촬영계정 비밀번호 /persistent:yes

if not exist logs mkdir logs
python sync_footage_to_sheet.py >> "logs\sync_%date:~0,4%%date:~5,2%%date:~8,2%.log" 2>&1
