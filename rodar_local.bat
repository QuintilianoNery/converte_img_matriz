@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo  Conversor Imagem -> Bordado (Local)
echo ==========================================

REM Verifica winget
where winget >nul 2>nul
if errorlevel 1 (
  echo [ERRO] Winget nao encontrado. No Windows 11 normalmente ja vem instalado.
  echo Abra a Microsoft Store e instale "App Installer" e tente novamente.
  pause
  exit /b 1
)

REM Verifica python
where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instalando Python 3.11 via winget...
  winget install --id Python.Python.3.11 -e --accept-package-agreements --accept-source-agreements
)

REM Recarrega PATH (nem sempre necessario, mas ajuda)
where python >nul 2>nul
if errorlevel 1 (
  echo [ERRO] Python ainda nao foi encontrado no PATH.
  echo Reinicie o computador ou feche e abra o Prompt, e rode este BAT novamente.
  pause
  exit /b 1
)

echo Usando:
python --version

cd /d "%~dp0server"

if not exist ".venv" (
  echo Criando ambiente virtual...
  python -m venv .venv
)

call ".venv\Scripts\activate"

echo Atualizando pip...
python -m pip install --upgrade pip

echo Instalando dependencias...
pip install -r requirements.txt

echo Iniciando servidor...
start "" http://127.0.0.1:8000/docs/
uvicorn app:app --host 127.0.0.1 --port 8000

pause