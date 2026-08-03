@echo off
:: 1. Force Python to output UTF-8 so emojis do not crash the engine
set PYTHONIOENCODING=utf-8

:: 2. Ensure this path points to your ACTUAL updated code (Verify C: vs D:)
cd /d C:\AuctionBot

echo ========================================= >> server_logs.txt
echo WEEKLY FLEET STARTED: %date% %time% >> server_logs.txt
echo ========================================= >> server_logs.txt

echo Running MSTC...
python run_mstc.py >> server_logs.txt 2>&1

echo Cleaning up background Chrome processes and waiting 60 seconds...
taskkill /F /IM chrome.exe /T >nul 2>&1
taskkill /F /IM chromedriver.exe /T >nul 2>&1
timeout /t 60 /nobreak >nul

echo Running Metal Junction...
python run_mjunction.py >> server_logs.txt 2>&1

:: Final cleanup before closing
taskkill /F /IM chrome.exe /T >nul 2>&1
taskkill /F /IM chromedriver.exe /T >nul 2>&1
timeout /t 60 /nobreak >nul

echo Running IREPS Main...
python run_ireps.py >> server_logs.txt 2>&1

echo Cleaning up background Chrome processes and waiting 60 seconds...
taskkill /F /IM chrome.exe /T >nul 2>&1
taskkill /F /IM chromedriver.exe /T >nul 2>&1

echo WEEKLY FLEET FINISHED: %date% %time% >> server_logs.txt