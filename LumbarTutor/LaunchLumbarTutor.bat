@echo off
echo Starting Lumbar Tutor Environment...

:: 1. Define your file paths here (Note the change to the CONFIG_DIR)
set SLICER_PATH="C:\Users\hernia\AppData\Local\NA-MIC\Slicer 5.2.2\Slicer.exe"
set PLUS_SERVER_PATH="C:\Users\hernia\PlusApp-2.8.0.20190617-Telemed-Win32\bin\PlusServerLauncher.exe"
set PLUS_CONFIG_DIR="C:\Users\hernia\Documents\Denesh\LumbarTutor\Config"

:: 2. Start the PLUS Server minimized in a separate window
echo Launching PLUS Server...
start "PLUS Server" /MIN %PLUS_SERVER_PATH% --connect --device-set-configuration-dir=%PLUS_CONFIG_DIR%

:: 3. Give PLUS a few seconds to boot up hardware before Slicer tries to connect
echo Waiting for PLUS hardware to initialize...
timeout /t 5 /nobreak

:: 4. Start 3D Slicer and launch directly into the module
echo Launching 3D Slicer...
start "3D Slicer" %SLICER_PATH% --python-code "slicer.modules.lumbartutor.widgetRepresentation();slicer.modules.LumbarTutorWidget.launchGuideletButton.click()"

echo Done!
exit