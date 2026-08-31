@echo off
chcp 65001 >nul
setlocal
set "HERE=%~dp0"
set "PYTHONIOENCODING=utf-8"

where py >nul 2>nul
if not errorlevel 1 goto haspy
where python >nul 2>nul
if not errorlevel 1 goto haspython

echo 이 컴퓨터에 파이썬이 설치되어 있지 않습니다. https://python.org 에서 설치 후 다시 실행하세요.
pause
goto :eof

:haspy
py -3 "%HERE%pyrun.py" %1
goto :eof

:haspython
python "%HERE%pyrun.py" %1
goto :eof
