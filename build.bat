@echo off
setlocal

set ROOT=%~dp0
set HOOK=%ROOT%target\PyInstaller\fbs_pyinstaller_hook.py

:: Generate fbs runtime hook (injects app_name/version into frozen binary)
if not exist "%ROOT%target\PyInstaller" mkdir "%ROOT%target\PyInstaller"
(
  echo import importlib
  echo module = importlib.import_module('fbs_runtime._frozen'^)
  echo module.BUILD_SETTINGS = {'app_name': 'Vial', 'version': '0.7.5', 'author': 'xyz'}
) > "%HOOK%"

:: Freeze
venv\Scripts\python -m PyInstaller ^
  --name "Vial" ^
  --noupx ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --contents-directory "." ^
  --icon "%ROOT%src\main\icons\Icon.ico" ^
  --distpath "%ROOT%target" ^
  --specpath "%ROOT%target\PyInstaller" ^
  --workpath "%ROOT%target\PyInstaller" ^
  --add-data "%ROOT%src\main\resources\base;." ^
  --add-data "%ROOT%src\main\icons\Icon.ico;." ^
  --paths "%ROOT%src\main\python" ^
  --runtime-hook "%HOOK%" ^
  "%ROOT%src\main\python\main.py"

echo.
echo Done. Portable app is in: target\Vial\
echo Zip that folder and share it.
