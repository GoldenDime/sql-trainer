@echo off
cd /d "%~dp0"
where pyw >nul 2>nul && (start "" pyw -3 trainer.py & exit /b)
where pythonw >nul 2>nul && (start "" pythonw trainer.py & exit /b)
where python >nul 2>nul && (python trainer.py & exit /b)
echo Python 3.11+ not found.
echo Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
pause
