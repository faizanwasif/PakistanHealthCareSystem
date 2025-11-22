@echo off
echo Checking Python environment...

REM Check if venv exists
if not exist "venv\" (
    echo Virtual environment not found. Creating venv...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment. Make sure Python is installed.
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
)

REM Activate venv
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if requirements are installed by checking for a key package
python -c "import flask" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
    echo Dependencies installed successfully.
)

REM Run the application
echo Starting application...
python backend\main.py

pause
