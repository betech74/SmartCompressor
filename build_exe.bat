@echo off
setlocal

cd /d "%~dp0"

set "PYTHON=%~dp0.venv\Scripts\python.exe"
set "SPEC=%~dp0SmartCompressor.spec"
set "OUTPUT=%~dp0dist\SmartCompressor.exe"

echo ================================================
echo   Smart Compressor - compilation de l'EXE
echo ================================================
echo.

if not exist "%PYTHON%" (
    echo [ERREUR] Python du venv introuvable :
    echo          %PYTHON%
    echo.
    echo Creez d'abord le venv puis installez requirements-dev.txt.
    goto :failed
)

if not exist "%SPEC%" (
    echo [ERREUR] Fichier spec introuvable :
    echo          %SPEC%
    goto :failed
)

echo [1/3] Verification de PyInstaller...
"%PYTHON%" -c "import PyInstaller"
if errorlevel 1 (
    echo.
    echo [ERREUR] PyInstaller n'est pas installe dans le venv.
    echo Lancez :
    echo   "%PYTHON%" -m pip install -r requirements-dev.txt
    goto :failed
)
echo        PyInstaller disponible.

echo.
echo [2/3] Compilation en cours...
echo        La sortie detaillee de PyInstaller va s'afficher ci-dessous.
echo.
"%PYTHON%" -m PyInstaller --clean --noconfirm "%SPEC%"
if errorlevel 1 (
    echo.
    echo [ECHEC] La compilation a echoue.
    goto :failed
)

echo.
echo [3/3] Verification de l'EXE...
if not exist "%OUTPUT%" (
    echo [ERREUR] Compilation terminee mais EXE introuvable :
    echo          %OUTPUT%
    goto :failed
)

for %%F in ("%OUTPUT%") do echo [OK] EXE genere : %%~fF (%%~zF octets)
echo.
echo Compilation terminee avec succes.
goto :done

:failed
set "EXIT_CODE=1"
echo.
echo Consultez les messages ci-dessus pour le detail de l'erreur.
goto :finish

:done
set "EXIT_CODE=0"

:finish
echo.
pause
exit /b %EXIT_CODE%
