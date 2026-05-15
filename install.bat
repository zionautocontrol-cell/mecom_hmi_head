@echo off
title MECOM HMI HEAD Installer
color 0B
echo ==========================================
echo  MECOM HMI HEAD System Installer
echo ==========================================
echo.

cd /d "%~dp0"

echo [1/4] Checking Python...

python -c "import sys; print(f'OK {sys.version_info[0]}.{sys.version_info[1]}')" > "%TEMP%\pyver.txt" 2>&1
if %errorlevel% EQU 0 (
    set /p PYVER=<"%TEMP%\pyver.txt"
    set PYTHON_CMD=python
    goto :PYTHON_OK
)

py -3 -c "import sys; print(f'OK {sys.version_info[0]}.{sys.version_info[1]}')" > "%TEMP%\pyver.txt" 2>&1
if %errorlevel% EQU 0 (
    set /p PYVER=<"%TEMP%\pyver.txt"
    set PYTHON_CMD=py -3
    goto :PYTHON_OK
)

for %%p in (
    "C:\Program Files\Python312\python.exe"
    "C:\Program Files\Python311\python.exe"
    "C:\Program Files (x86)\Python312\python.exe"
    "C:\Program Files (x86)\Python311\python.exe"
    "%LocalAppData%\Programs\Python\Python312\python.exe"
    "%LocalAppData%\Programs\Python\Python311\python.exe"
) do (
    if exist %%p (
        "%%~p" -c "import sys; print(f'OK {sys.version_info[0]}.{sys.version_info[1]}')" > "%TEMP%\pyver.txt" 2>&1
        if exist "%TEMP%\pyver.txt" ( set /p PYVER=<"%TEMP%\pyver.txt" )
        set PYTHON_CMD=%%~p
        goto :PYTHON_OK
    )
)

:DOWNLOAD_PYTHON
echo   Installing Python 3.12...

set PY_INSTALLER=%TEMP%\python-3.12.4-amd64.exe
echo   Downloading...
powershell -Command "try { Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe' -OutFile '%TEMP%\python-3.12.4-amd64.exe' -UseBasicParsing; exit 0 } catch { exit 1 }"
if %errorlevel% NEQ 0 (
    echo   Download failed. Install Python manually from python.org
    pause
    exit /b 1
)

echo   Installing (this may take a minute)...
start /w "" "%PY_INSTALLER%" /quiet PrependPath=1 Include_test=0
del "%PY_INSTALLER%" 2>NUL

if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set PYTHON_CMD=%LocalAppData%\Programs\Python\Python312\python.exe
if exist "%ProgramFiles%\Python312\python.exe" set PYTHON_CMD=%ProgramFiles%\Python312\python.exe
if exist "%ProgramFiles(x86)%\Python312\python.exe" set PYTHON_CMD=%ProgramFiles(x86)%\Python312\python.exe

if defined PYTHON_CMD (
    "%PYTHON_CMD%" -c "import sys; print(f'OK {sys.version_info[0]}.{sys.version_info[1]}')" > "%TEMP%\pyver.txt" 2>&1
    if %errorlevel% EQU 0 (
        set /p PYVER=<"%TEMP%\pyver.txt"
        goto :PYTHON_OK
    )
)

echo   Installation failed. Install Python 3.12 manually from python.org
pause
exit /b 1

:PYTHON_OK
del "%TEMP%\pyver.txt" 2>NUL

:: Check for Microsoft Store Python (skip it)
"%PYTHON_CMD%" -c "import sys; exit(0 if 'WindowsApps' in sys.executable or 'pythoncore' in sys.executable else 1)" 2>NUL
if %errorlevel% EQU 0 (
    echo   Detected Microsoft Store Python - installing real Python...
    goto :DOWNLOAD_PYTHON
)

echo   %PYVER% (%PYTHON_CMD%)

echo [2/4] Installing libraries...
call %PYTHON_CMD% -m pip install --upgrade pip -q
call %PYTHON_CMD% -m pip install -r requirements.txt
if %errorlevel% EQU 0 (
    echo   Libraries installed OK
    goto :CONTINUE
)

echo.
echo   pip install FAILED. Possible causes:
echo     1. No internet connection
echo     2. Windows Store Python (install real Python from python.org)
echo.
echo   Retry manually: %PYTHON_CMD% -m pip install -r requirements.txt
echo.
pause
exit /b 1

:CONTINUE

echo [3/7] Clearing previous deployment data...
del /f /q "realtime_data.json" 2>NUL
del /f /q "history_data.csv" 2>NUL
del /f /q "alarm_history.csv" 2>NUL
del /f /q "control_command.json" 2>NUL
del /f /q "mecom_data.db" 2>NUL
del /f /q "mecom_hmi.log" 2>NUL
del /f /q "password.json" 2>NUL
echo   Previous data cleared.

echo [4/8] Connection type...
echo   [1] RS485 (Serial/COM port)
echo   [2] Ethernet (Modbus TCP/IP)
set /p conn_type="  Select connection type (1 or 2, default=1): "
if "%conn_type%"=="" set conn_type=1
if "%conn_type%"=="2" goto :ETHERNET_SETUP

:RS485_SETUP
echo.
echo   --- RS485 (Serial) Configuration ---
set /p comport="  Enter COM port (default=COM6): "
if "%comport%"=="" set comport=COM6
echo %comport%|findstr /i "^COM" >nul
if errorlevel 1 set comport=COM%comport%
set /p rtu_slave="  Enter PLC slave ID (default=1): "
if "%rtu_slave%"=="" set rtu_slave=1
echo   Port set to %comport%, slave ID %rtu_slave%
powershell -Command "(Get-Content config.py) -replace 'MODBUS_PORT = \"(COM)?\d+\"', 'MODBUS_PORT = \"%comport%\"' | Set-Content config.py -Encoding UTF8"
powershell -Command "(Get-Content config.py) -replace 'MODBUS_SLAVE_ID = \d+', 'MODBUS_SLAVE_ID = %rtu_slave%' | Set-Content config.py -Encoding UTF8"
powershell -Command "(Get-Content config.py) -replace \"MODBUS_MODE = '.*?'\", \"MODBUS_MODE = 'rtu'\" | Set-Content config.py -Encoding UTF8"
echo   Config updated
goto :SITE_SETUP

:ETHERNET_SETUP
echo.
echo   --- Ethernet (TCP) Configuration ---
set /p modbus_host="  Enter PLC IP address (default=192.168.0.1): "
if "%modbus_host%"=="" set modbus_host=192.168.0.1
set /p modbus_tcp_port="  Enter PLC TCP port (default=502): "
if "%modbus_tcp_port%"=="" set modbus_tcp_port=502
set /p tcp_slave="  Enter PLC slave ID (default=1): "
if "%tcp_slave%"=="" set tcp_slave=1
echo   Ethernet config: %modbus_host%:%modbus_tcp_port% (slave %tcp_slave%)
powershell -Command "(Get-Content config.py) -replace \"MODBUS_MODE = '.*?'\", \"MODBUS_MODE = 'tcp'\" | Set-Content config.py -Encoding UTF8"
powershell -Command "(Get-Content config.py) -replace 'MODBUS_HOST = \".*?\"', 'MODBUS_HOST = \"%modbus_host%\"' | Set-Content config.py -Encoding UTF8"
powershell -Command "(Get-Content config.py) -replace 'MODBUS_TCP_PORT = \d+', 'MODBUS_TCP_PORT = %modbus_tcp_port%' | Set-Content config.py -Encoding UTF8"
powershell -Command "(Get-Content config.py) -replace 'MODBUS_SLAVE_ID = \d+', 'MODBUS_SLAVE_ID = %tcp_slave%' | Set-Content config.py -Encoding UTF8"
echo   Config updated

:SITE_SETUP

echo [5/8] Site setup...
set /p site_id="  Enter site name (default=default): "
if "%site_id%"=="" set site_id=default
echo   Site set to %site_id%
powershell -Command "(Get-Content config.py) -replace 'SITE_ID = \".*?\"', 'SITE_ID = \"%site_id%\"' | Set-Content config.py -Encoding UTF8"
if not exist "sites\%site_id%" (
    echo   Creating site directory...
    mkdir "sites\%site_id%" >NUL 2>&1
    copy "sites\default\*.html" "sites\%site_id%\" >NUL 2>&1
    copy "sites\default\*.png" "sites\%site_id%\" >NUL 2>&1
)
echo   Config updated

echo [6/8] Head-office connection setup...
set /p use_head="  Connect to head-office server? (Y/n): "
if /i "%use_head%"=="n" (
    powershell -Command "(Get-Content config.py) -replace 'HEAD_ENABLED = True', 'HEAD_ENABLED = False' | Set-Content config.py -Encoding UTF8"
    echo   Head-office communication disabled.
    goto :SHORTCUTS
)
set /p head_url="  Enter head-office server URL (default=http://localhost:8000): "
if "%head_url%"=="" set head_url=http://localhost:8000
powershell -Command "(Get-Content config.py) -replace 'HEAD_SERVER_URL = \".*?\"', 'HEAD_SERVER_URL = \"%head_url%\"' | Set-Content config.py -Encoding UTF8"
set /p api_key="  Enter API key: "
powershell -Command "(Get-Content config.py) -replace 'API_KEY = \".*?\"', 'API_KEY = \"%api_key%\"' | Set-Content config.py -Encoding UTF8"
echo   Head-office connection enabled.

:SHORTCUTS
echo [7/8] Creating shortcuts...

> start_hmi.bat (
echo @echo off
echo title MECOM HMI System ^(RS485 Mode^)
echo color 0A
echo.
echo cd /d "%%~dp0"
echo set MECOM_MODBUS_MODE=rtu
echo echo [Head Client] starting...
echo start /b python head_client.py
echo echo [Modbus Worker] starting...
echo start /b python modbus_worker.py
echo echo [API Server] starting...
echo start /b python api_server.py
echo timeout /t 3 /nobreak ^> NUL
echo echo.
echo echo Opening dashboard at http://localhost:8501
echo streamlit run app.py
echo pause
)
echo   Created start_hmi.bat (RS485 mode)

> start_hmi_ethernet.bat (
echo @echo off
echo title MECOM HMI System ^(Ethernet Mode^)
echo color 0A
echo.
echo cd /d "%%~dp0"
echo set MECOM_MODBUS_MODE=tcp
echo echo [Head Client] starting...
echo start /b python head_client.py
echo echo [Modbus Worker] starting...
echo start /b python modbus_worker.py
echo echo [API Server] starting...
echo start /b python api_server.py
echo timeout /t 3 /nobreak ^> NUL
echo echo.
echo echo Opening dashboard at http://localhost:8501
echo streamlit run app.py
echo pause
)
echo   Created start_hmi_ethernet.bat (Ethernet mode)

if "%conn_type%"=="2" goto :SHORTCUT_ETHERNET

:SHORTCUT_RS485
powershell -Command ^
  $WSH = New-Object -ComObject WScript.Shell; ^
  $lnk = $WSH.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\MECOM HMI.lnk'); ^
  $lnk.TargetPath = '%~dp0start_hmi.bat'; ^
  $lnk.WorkingDirectory = '%~dp0'; ^
  $lnk.Save() >NUL 2>&1
if %errorlevel% EQU 0 (
    echo   Desktop shortcut created (RS485 mode)
)
goto :INSTALL_DONE

:SHORTCUT_ETHERNET
powershell -Command ^
  $WSH = New-Object -ComObject WScript.Shell; ^
  $lnk = $WSH.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\MECOM HMI.lnk'); ^
  $lnk.TargetPath = '%~dp0start_hmi_ethernet.bat'; ^
  $lnk.WorkingDirectory = '%~dp0'; ^
  $lnk.Save() >NUL 2>&1
if %errorlevel% EQU 0 (
    echo   Desktop shortcut created (Ethernet mode)
)

:INSTALL_DONE

echo.
echo ==========================================
echo  Installation Complete!
echo ==========================================
echo.
echo  Double-click "MECOM HMI" on your desktop
echo  URL: http://localhost:8501
echo.
pause
