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

set "APP_URL=http://127.0.0.1:8000/"

echo Encerrando instancias antigas do backend...
powershell -NoProfile -Command "$procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'uvicorn app:app --host 127.0.0.1 --port 8000' }; foreach($proc in $procs){ try { Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop } catch {} }"
timeout /t 1 /nobreak >nul

echo Iniciando backend (mesma janela, em background)...
start "" /b "%CD%\.venv\Scripts\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8000

echo Aguardando backend ficar pronto...
set /a BACKEND_TRIES=0

:wait_backend
set /a BACKEND_TRIES+=1
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri '%APP_URL%' -TimeoutSec 2; if ($r.StatusCode -ge 200) { exit 0 } else { exit 1 } } catch { exit 1 }"

if errorlevel 1 (
  if !BACKEND_TRIES! GEQ 45 (
    echo [ERRO] Backend nao respondeu a tempo em %APP_URL%
    echo Verifique os logs acima para detalhes do backend.
    pause
    exit /b 1
  )
  timeout /t 1 /nobreak >nul
  goto :wait_backend
)

echo Backend pronto. Abrindo frontend...
start "" "%APP_URL%?v=%RANDOM%"

pause