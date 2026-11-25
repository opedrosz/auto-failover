@echo off
REM Iniciar Auto-Failover - diagnostico
python "%~dp0cli.py" doctor
python "%~dp0cli.py" status
pause
