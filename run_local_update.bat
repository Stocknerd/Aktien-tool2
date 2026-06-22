@echo off
:: =========================================================================
:: Schatzsuche 4.0: Automatisches lokales Datenupdate & AWS-Deployment (LOGGING)
:: =========================================================================
chcp 65001 > nul
setlocal enabledelayedexpansion

cd /d "%~dp0"
mkdir logs 2>nul

set LOGFILE=%~dp0logs\local_update.log

echo ========================================================================= >> "%LOGFILE%"
echo 📊 [%date% %time%] Starte automatisiertes Datenupdate... >> "%LOGFILE%"
echo ========================================================================= >> "%LOGFILE%"

:: 1. Lokales yfinance Update
echo [%date% %time%] 📈 [1/3] Starte yfinance update_csv_local.py... >> "%LOGFILE%"
.\.venv\Scripts\python.exe -u update_csv_local.py >> "%LOGFILE%" 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo ❌ [%date% %time%] ERROR: Lokales Datenupdate fehlgeschlagen! >> "%LOGFILE%"
    exit /b %ERRORLEVEL%
)
echo [%date% %time%] ✅ [1/3] yfinance Update erfolgreich beendet. >> "%LOGFILE%"

:: 2. Committe und pushe Daten auf GitHub
echo [%date% %time%] 💾 [2/3] Committe und pushe stock_data.csv auf GitHub... >> "%LOGFILE%"
git add stock_data.csv >> "%LOGFILE%" 2>&1
git commit -m "Auto-update stock data (%date% %time%)" >> "%LOGFILE%" 2>&1
git push origin main >> "%LOGFILE%" 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo ❌ [%date% %time%] ERROR: Git Push fehlgeschlagen! >> "%LOGFILE%"
    exit /b %ERRORLEVEL%
)
echo [%date% %time%] ✅ [2/3] Git Push erfolgreich beendet. >> "%LOGFILE%"

:: 3. Trigger Remote Deploy auf AWS Server via SSH
echo [%date% %time%] 🚀 [3/3] Trigger Remote Deployment auf AWS Server... >> "%LOGFILE%"

:: Find correct SSH Key
set SSH_KEY=
if exist "%USERPROFILE%\Downloads\LightsailDefaultKey-eu-central-1.pem" set SSH_KEY=%USERPROFILE%\Downloads\LightsailDefaultKey-eu-central-1.pem
if exist "C:\Users\fhofm\Downloads\LightsailDefaultKey-eu-central-1.pem" set SSH_KEY=C:\Users\fhofm\Downloads\LightsailDefaultKey-eu-central-1.pem
if exist "%USERPROFILE%\.ssh\aws-eb" set SSH_KEY=%USERPROFILE%\.ssh\aws-eb

if "%SSH_KEY%"=="" (
    echo ❌ [%date% %time%] ERROR: Kein SSH-Key gefunden! >> "%LOGFILE%"
    exit /b 1
)
echo [%date% %time%] SSH Key used: %SSH_KEY% >> "%LOGFILE%"

ssh -o StrictHostKeyChecking=no -i "%SSH_KEY%" ubuntu@3.71.191.12 "cd /home/ubuntu/aktien-tool2 && bash deploy.sh" >> "%LOGFILE%" 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo ❌ [%date% %time%] ERROR: Remote AWS Deployment fehlgeschlagen! >> "%LOGFILE%"
    exit /b %ERRORLEVEL%
)
echo [%date% %time%] ✅ [3/3] AWS Deployment erfolgreich beendet. >> "%LOGFILE%"

echo ========================================================================= >> "%LOGFILE%"
echo 🎉 [%date% %time%] Datenupdate und Server-Deployment ERFOLGREICH! >> "%LOGFILE%"
echo ========================================================================= >> "%LOGFILE%"

