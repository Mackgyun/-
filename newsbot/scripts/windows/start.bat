@echo off
rem Chungnyun Briefing - run in this window (closing the window stops it).
rem For always-on running use install-autostart.ps1
rem Do not run this while the autostart task is running (same port 8000).
chcp 65001 >nul
cd /d "%~dp0..\.."
".venv\Scripts\python.exe" -m newsbot
pause
