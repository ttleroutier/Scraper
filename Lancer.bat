@echo off
REM ===========================================================
REM   MAPS LEAD FINDER - Lanceur autonome
REM   Installe automatiquement tout ce qui manque.
REM   Tout reste dans le dossier du projet.
REM ===========================================================

title Maps Lead Finder
cd /d "%~dp0"
setlocal EnableDelayedExpansion


REM ==================================== 0. PARAMETRES
REM Mettre a 1 pour forcer Python local meme si Python existe deja sur le PC
set "FORCE_LOCAL_PYTHON=0"

set "PYTHON_VERSION=3.12.6"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-amd64.exe"

set "LOCAL_PY=%CD%\python\python.exe"
set "VPY=%CD%\.venv\Scripts\python.exe"
set "PLAYWRIGHT_BROWSERS_PATH=%CD%\browsers"
set "PIP_CACHE_DIR=%CD%\.pipcache"

echo ============================================
echo            MAPS LEAD FINDER
echo ============================================
echo.


REM ==================================== 1. FICHIERS DU PROJET
if not exist "app.py" (
    echo [ERREUR] app.py introuvable.
    echo Placez Lancer.bat dans le dossier du projet.
    echo.
    pause & exit /b
)

if not exist "requirements.txt" (
    echo requirements.txt absent, generation automatique...
    (
        echo streamlit^>=1.36
        echo playwright^>=1.45
        echo pandas^>=2.2
        echo openpyxl^>=3.1
        echo requests^>=2.32
        echo beautifulsoup4^>=4.12
    ) > requirements.txt
    echo Fichier cree.
    echo.
)


REM ==================================== 2. OUTIL DE TELECHARGEMENT
set "HAS_CURL=1"
curl --version >nul 2>&1
if errorlevel 1 set "HAS_CURL=0"


REM ==================================== 3. RECHERCHE DE PYTHON
call :FIND_PYTHON

if not defined PY (
    echo Python 3.10 ou superieur introuvable.
    echo Installation automatique en cours...
    echo.
    call :CHECK_INTERNET
    call :INSTALL_PYTHON
    call :FIND_PYTHON
)

if not defined PY (
    echo.
    echo [ERREUR] Python n'a pas pu etre installe automatiquement.
    echo Installez-le manuellement : https://www.python.org/downloads/
    echo Cochez "Add Python to PATH", puis relancez ce fichier.
    echo.
    pause & exit /b
)

echo Python detecte : !PY!


REM ==================================== 4. ENVIRONNEMENT VIRTUEL
set "NEED_INSTALL=0"

if not exist "%VPY%" (
    echo Creation de l'environnement virtuel...
    !PY! -m venv .venv
    if errorlevel 1 (
        echo [ERREUR] Creation de l'environnement virtuel impossible.
        echo.
        pause & exit /b
    )
    set "NEED_INSTALL=1"
)


REM ==================================== 5. DEPENDANCES PYTHON
if "!NEED_INSTALL!"=="0" (
    "%VPY%" -c "import streamlit, playwright, pandas, openpyxl, requests, bs4" >nul 2>&1
    if errorlevel 1 (
        echo Dependances manquantes ou incompletes.
        set "NEED_INSTALL=1"
    )
)

if "!NEED_INSTALL!"=="0" (
    if not exist ".venv\requirements.installed" (
        set "NEED_INSTALL=1"
    ) else (
        fc /b requirements.txt .venv\requirements.installed >nul 2>&1
        if errorlevel 1 (
            echo requirements.txt a change depuis la derniere installation.
            set "NEED_INSTALL=1"
        )
    )
)

if "!NEED_INSTALL!"=="1" (
    call :CHECK_INTERNET
    echo.
    echo Installation des dependances, patientez 3 a 5 minutes...
    echo.
    "%VPY%" -m pip install --upgrade pip
    "%VPY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERREUR] Installation des dependances echouee.
        echo Verifiez votre connexion Internet puis relancez.
        echo.
        pause & exit /b
    )
    copy /y requirements.txt .venv\requirements.installed >nul
    echo Dependances installees.
)


REM ==================================== 6. DOSSIERS DE TRAVAIL
if not exist "data" mkdir data
if not exist "browsers" mkdir browsers


REM ==================================== 7. NAVIGATEUR CHROMIUM
"%VPY%" -c "import os,sys;from playwright.sync_api import sync_playwright;p=sync_playwright().start();sys.exit(0 if os.path.exists(p.chromium.executable_path) else 1)" >nul 2>&1
if errorlevel 1 (
    call :CHECK_INTERNET
    echo.
    echo Telechargement du navigateur Chromium (environ 150 Mo)...
    "%VPY%" -m playwright install chromium
    if errorlevel 1 (
        echo.
        echo [ERREUR] Telechargement de Chromium echoue.
        echo.
        pause & exit /b
    )
    echo Navigateur installe.
)


REM ==================================== 8. LANCEMENT
echo.
echo ============================================
echo   Tous les prerequis sont valides.
echo   Demarrage de l'interface...
echo.
echo   NE FERMEZ PAS cette fenetre pendant
echo   l'utilisation de l'outil.
echo   Pour arreter : Ctrl + C
echo ============================================
echo.

"%VPY%" -m streamlit run app.py

echo.
echo Application fermee.
pause
exit /b


REM ###########################################################
REM                      SOUS-ROUTINES
REM ###########################################################

:FIND_PYTHON
set "PY="

REM --- a. Python local du projet (prioritaire)
if exist "%LOCAL_PY%" (
    "%LOCAL_PY%" -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY="%LOCAL_PY%""
)

REM --- b. Python deja installe sur l'ordinateur
if "%FORCE_LOCAL_PYTHON%"=="0" (
    if not defined PY (
        for %%C in ("py -3" "python") do (
            if not defined PY (
                %%~C -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
                if not errorlevel 1 set "PY=%%~C"
            )
        )
    )
    if not defined PY (
        for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
            if not defined PY (
                if exist "%%D\python.exe" (
                    "%%D\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
                    if not errorlevel 1 set "PY="%%D\python.exe""
                )
            )
        )
    )
)
exit /b


:INSTALL_PYTHON
echo Telechargement de Python %PYTHON_VERSION%...

if "%HAS_CURL%"=="1" (
    curl -L -o "%TEMP%\python-setup.exe" "%PYTHON_URL%"
) else (
    powershell -NoProfile -Command ^
        "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%TEMP%\python-setup.exe'"
)

if not exist "%TEMP%\python-setup.exe" (
    echo [ERREUR] Telechargement de Python impossible.
    exit /b
)

echo Installation dans "%CD%\python"...
"%TEMP%\python-setup.exe" /quiet TargetDir="%CD%\python" ^
    InstallAllUsers=0 PrependPath=0 Include_pip=1 ^
    Include_launcher=0 AssociateFiles=0 Shortcuts=0 Include_test=0

del "%TEMP%\python-setup.exe" >nul 2>&1
echo Python installe.
exit /b


:CHECK_INTERNET
if "%HAS_CURL%"=="1" (
    curl -s -I https://pypi.org >nul 2>&1
) else (
    ping -n 1 pypi.org >nul 2>&1
)
if errorlevel 1 (
    echo.
    echo [ERREUR] Aucune connexion Internet detectee.
    echo Connectez-vous puis relancez ce fichier.
    echo.
    pause & exit
)
exit /b
