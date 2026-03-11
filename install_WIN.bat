@echo off
setlocal

set "PROJECT_PARENT=%USERPROFILE%\Desktop"
set "REPO_URL=https://github.com/teacher-tta/National-Youth-Tech-Championship-2026"
set "REPO_NAME=National-Youth-Tech-Championship-2026"
set "VENV_NAME=venv"

echo Checking for Python 3.13...

py -3.13 --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo Python 3.13 is required but was not found.
    echo.
    echo Please install Python 3.13 from:
    echo https://www.python.org/downloads/release/python-31312/
    echo.
    echo IMPORTANT: During installation, check:
    echo     [x] Use admin privileges when installing py.exe
    echo     [x] Add python.exe to PATH
    echo.
    echo After installing Python, run this script again.
    echo.
    pause
    exit /b 1
)

echo Python 3.13 detected.

echo Checking for Git...
where git >nul 2>&1
if errorlevel 1 (
    echo.
    echo Git is required but was not found.
    echo.
    echo Please install Git from:
    echo https://git-scm.com/download/win
    echo.
    echo After installing Git, run this script again.
    echo.
    pause
    exit /b 1
)

echo Git detected.

echo Moving to Desktop...
cd /d "%PROJECT_PARENT%"

echo Cloning repository...

if not exist "%REPO_NAME%" (
    git clone "%REPO_URL%"
    if errorlevel 1 (
        echo Failed to clone repository.
        pause
        exit /b 1
    )
) else (
    echo Repository already exists. Skipping clone.
)

echo Entering repository folder...
cd /d "%PROJECT_PARENT%\%REPO_NAME%"

echo Creating requirements.txt...

(
echo ugot
echo opencv-python
echo ipykernel
echo ipython
echo ultralytics
) > requirements.txt

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

echo Installing dependencies...
python -m pip install -r requirements.txt

echo -----------------------------------------------
echo.
echo Setup complete!
echo Project located at:
echo %PROJECT_PARENT%\%REPO_NAME%
echo.

pause
endlocal