@echo off
setlocal

set "PROJECT_NAME=nytc"
set "PROJECT_DIR=%USERPROFILE%\Desktop\%PROJECT_NAME%"
set "VENV_NAME=venv"

echo Creating project directory...
if not exist "%PROJECT_DIR%" mkdir "%PROJECT_DIR%"
cd /d "%PROJECT_DIR%"

echo Creating requirements.txt...
(
    echo ugot
    echo opencv-python
    echo ipykernel
    echo ipython
    echo ultralytics
) > requirements.txt

echo Checking for Python 3.13...
py -3.13 --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.13 is not installed or not available through the py launcher.
    echo Please install Python 3.13 first, then run this script again.
    pause
    exit /b 1
)

echo Creating virtual environment...
py -3.13 -m venv "%VENV_NAME%"
if errorlevel 1 (
    echo Failed to create virtual environment.
    pause
    exit /b 1
)

echo Activating virtual environment...
call "%VENV_NAME%\Scripts\activate.bat"

echo Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip.
    pause
    exit /b 1
)

echo Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo ---------------------------------
echo Setup complete!
echo Project created at: %PROJECT_DIR%
echo.

echo Opening VS code...
code

echo.

pause
endlocal