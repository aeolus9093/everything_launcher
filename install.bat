@echo off
chcp 65001 >nul
setlocal
set "SRC=%~dp0PyRun.exe"
set "APPDIR=%LOCALAPPDATA%\PyRun"

if not exist "%SRC%" (
    echo PyRun.exe 파일을 찾을 수 없습니다. 이 install.bat과 같은 폴더에 PyRun.exe를 넣어주세요.
    pause
    goto :eof
)

if not exist "%APPDIR%" mkdir "%APPDIR%"
copy /y "%SRC%" "%APPDIR%\PyRun.exe" >nul

reg add "HKCU\Software\Classes\PyRun.pyfile" /ve /d "Python 파일 (PyRun)" /f >nul
reg add "HKCU\Software\Classes\PyRun.pyfile\shell\open\command" /ve /d "\"%APPDIR%\PyRun.exe\" \"%%1\"" /f >nul
reg add "HKCU\Software\Classes\.py\OpenWithProgids" /v "PyRun.pyfile" /d "" /f >nul

echo.
echo 설치 완료: %APPDIR%\PyRun.exe
echo.
echo 이제 .py 파일에서 마우스 오른쪽 클릭 -^> 연결 프로그램 -^> "Python 파일 (PyRun)" 선택하고
echo "항상 이 앱을 사용하여 .py 파일 열기" 체크하면, 그 다음부터는 더블클릭만으로 실행됩니다.
echo (Windows 보안 정책상 기본 프로그램 지정은 이렇게 한 번은 직접 선택해야 합니다.)
echo.
pause
