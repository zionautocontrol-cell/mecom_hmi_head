@echo off
title MECOM HMI System (Ethernet Mode)
color 0A

cd /d "%~dp0"
set MECOM_MODBUS_MODE=tcp
echo [Head Client] starting...
start /b python head_client.py
echo [Modbus Worker] starting... (Ethernet/TCP mode)
start /b python modbus_worker.py
echo [API Server] starting...
start /b python api_server.py
timeout /t 3 /nobreak > NUL
echo.
echo Opening dashboard at http://localhost:8501
streamlit run app.py
pause
