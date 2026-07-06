@echo off
echo Starting Lumbar Tutor Environment...

:: 1. Define your file paths here
set SLICER_PATH="C:\Users\Robert\AppData\Local\slicer.org\Slicer 5.8.1\Slicer.exe"
set PLUS_SERVER_PATH="C:\PlusApp\bin\PlusServer.exe"
set PLUS_CONFIG_PATH="C:\Users\Robert\LumbarTutor\PlusDeviceSet_Server.xml"

:: 2. Start the PLUS Server minimized in a separate window
echo Launching PLUS Server...
start "PLUS Server" /MIN %PLUS_SERVER_PATH% --config-file=%PLUS_CONFIG_PATH%

:: 3. Give PLUS a few seconds to boot up hardware before Slicer tries to connect
echo Waiting for PLUS hardware to initialize...
timeout /t 5 /nobreak

:: 4. Start 3D Slicer and launch directly into the module
echo Launching 3D Slicer...
start "3D Slicer" %SLICER_PATH% --module LumbarTutor

echo Done!
exit