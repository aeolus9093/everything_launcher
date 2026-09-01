@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".buildenv" (
    echo [빌드환경] base 환경 pyinstaller 충돌 방지용 격리 venv 생성 중...
    py -3 -m venv .buildenv
    ".buildenv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check pyinstaller
)

".buildenv\Scripts\python.exe" -m PyInstaller --onefile --console --name PyRun --distpath dist --workpath build --specpath build pyrun.py

echo.
echo 빌드 완료: dist\PyRun.exe
pause
