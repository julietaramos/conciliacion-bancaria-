@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title Conciliacion Bancaria

echo.
echo  ============================================
echo   Conciliacion Bancaria
echo  ============================================
echo.

:: ---- Verificar Python ----
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado.
    echo.
    echo  Para instalarlo:
    echo   1. Abri el navegador y entra a https://www.python.org/downloads/
    echo   2. Hace clic en el boton grande amarillo de descarga
    echo   3. Ejecuta el instalador
    echo   4. MUY IMPORTANTE: tilda la opcion "Add Python to PATH"
    echo   5. Hace clic en "Install Now"
    echo   6. Reinicia la computadora y volvé a hacer doble clic en este archivo
    echo.
    pause
    exit /b 1
)

:: ---- Verificar Node.js ----
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js no esta instalado.
    echo.
    echo  Para instalarlo:
    echo   1. Abri el navegador y entra a https://nodejs.org
    echo   2. Hace clic en el boton LTS (el de la izquierda)
    echo   3. Ejecuta el instalador con las opciones por defecto
    echo   4. Reinicia la computadora y volvé a hacer doble clic en este archivo
    echo.
    pause
    exit /b 1
)

:: ---- Instalar dependencias del backend (solo si faltan) ----
python -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
    echo [1/2] Instalando componentes necesarios...
    echo       Esto solo pasa la primera vez. Puede tardar unos minutos.
    echo.
    pip install -r backend\requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] No se pudieron instalar los componentes del backend.
        echo         Revisa que tengas conexion a internet e intentalo de nuevo.
        pause
        exit /b 1
    )
    echo.
) else (
    echo [1/2] Componentes del sistema: listos
)

:: ---- Instalar dependencias del frontend (solo si faltan) ----
if not exist "frontend\node_modules" (
    echo [2/2] Instalando componentes de la interfaz...
    echo       Esto solo pasa la primera vez. Puede tardar unos minutos.
    echo.
    cd frontend
    call npm install
    if errorlevel 1 (
        cd ..
        echo.
        echo [ERROR] No se pudieron instalar los componentes del frontend.
        echo         Revisa que tengas conexion a internet e intentalo de nuevo.
        pause
        exit /b 1
    )
    cd ..
    echo.
) else (
    echo [2/2] Componentes de la interfaz: listos
)

:: ---- Crear archivo de configuracion si no existe ----
if not exist "backend\.env" (
    echo PORT=5000>backend\.env
    echo ALLOWED_ORIGINS=http://localhost:5173>>backend\.env
)

echo.
echo  Iniciando la aplicacion...
echo.

:: ---- Iniciar backend ----
cd /d "%~dp0backend\src"
start "Backend - Conciliacion" /min cmd /k python -m uvicorn main:app --port 5000
cd /d "%~dp0"

timeout /t 5 /nobreak >nul

:: ---- Iniciar frontend ----
cd /d "%~dp0frontend"
start "Frontend - Conciliacion" /min cmd /k npm run dev
cd /d "%~dp0"

timeout /t 6 /nobreak >nul

:: ---- Abrir navegador ----
start http://localhost:5173

echo.
echo  ============================================
echo   Aplicacion iniciada.
echo.
echo   Se abrio automaticamente en el navegador.
echo   Si no se abrio, ingresa manualmente a:
echo      http://localhost:5173
echo.
echo   Para CERRAR la aplicacion cuando termines:
echo   Busca en la barra de tareas las ventanas
echo   "Backend - Conciliacion" y
echo   "Frontend - Conciliacion" y cerralas.
echo  ============================================
echo.
pause
