@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup.bat first.
  pause
  exit /b 1
)
echo Running syntax validation...
".venv\Scripts\python.exe" -m compileall -q .
if errorlevel 1 goto failed
echo Running automated tests...
".venv\Scripts\python.exe" -m pytest -v
if errorlevel 1 goto failed
echo Running installation smoke test...
".venv\Scripts\python.exe" smoke_test.py
if errorlevel 1 goto failed
echo.
echo All local checks completed successfully.
pause
exit /b 0
:failed
echo.
echo One or more checks failed. Read the error output above.
pause
exit /b 1
