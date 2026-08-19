@echo off
title Maps Lead Finder
cd /d "%~dp0"

echo ============================================
echo            MAPS LEAD FINDER
echo ============================================
echo.

REM --- Verification de Python -------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe sur cet ordinateur.
    echo Telechargez-le sur https://www.python.org/downloads/
    echo Cochez "Add Python to PATH" pendant l'installation.
    echo.
    pause
    exit /b
)

REM --- Premiere utilisation : installation automatique -------
if not exist ".venv\Scripts\activate.bat" (
    echo Premiere utilisation detectee.
    echo Installation en cours, cela peut prendre 5 minutes...
    echo.
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    playwright install chromium
    echo.
    echo Installation terminee.
    echo.
) else (
    call .venv\Scripts\activate.bat
)

REM --- Lancement --------------------------------------------
echo Demarrage de l'interface...
echo Ne fermez pas cette fenetre pendant l'utilisation.
echo.
streamlit run app.py

pause
