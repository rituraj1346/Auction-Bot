@echo off
cd C:\AuctionBot

echo ========================================= >> server_logs.txt
echo DAILY CATALOGUES STARTED: %date% %time% >> server_logs.txt
echo ========================================= >> server_logs.txt

python run_catalogues.py >> server_logs.txt 2>&1

echo DAILY CATALOGUES FINISHED: %date% %time% >> server_logs.txt