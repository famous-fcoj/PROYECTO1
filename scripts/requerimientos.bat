@echo off
echo ===============================================
echo    INSTALADOR CONMETAL - SISTEMA OT
echo ===============================================
echo.

echo [1/8] Verificando prerequisitos del sistema...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no encontrado. Instalando Python...
    powershell -Command "Start-Process 'https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe' -Wait"
    echo ✅ Python instalado. Por favor reinicia el instalador.
    pause
    exit
)

node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js no encontrado. Instalando Node.js...
    powershell -Command "Invoke-WebRequest -Uri 'https://nodejs.org/dist/v18.18.0/node-v18.18.0-x64.msi' -OutFile 'node-installer.msi'; Start-Process msiexec -ArgumentList '/i', 'node-installer.msi', '/quiet', '/norestart' -Wait; Remove-Item 'node-installer.msi'"
    echo ✅ Node.js instalado.
)

echo [2/8] Instalando extensiones de VS Code...
code --install-extension ms-python.python
code --install-extension batisteo.vscode-django
code --install-extension bradlc.vscode-tailwindcss
code --install-extension esbenp.prettier-vscode
code --install-extension ms-vscode.vscode-json

echo [3/8] Configurando backend Django...
cd backend

echo    Creando entorno virtual...
python -m venv venv
call venv\Scripts\activate

echo    Instalando dependencias Python...
pip install --upgrade pip
pip install django==5.2.7
pip install mysqlclient
pip install django-cors-headers
pip install requests

echo    Generando requirements.txt...
pip freeze > requirements.txt

echo    Configurando base de datos...
python manage.py makemigrations
python manage.py migrate

echo [4/8] Configurando frontend React...
cd ..\frontend

echo    Instalando dependencias Node.js...
npm install
npm install -g vite

echo    Generando package.json si no existe...
if not exist package.json (
    echo {
    echo   "name": "conmetal-frontend",
    echo   "private": true,
    echo   "version": "0.0.0",
    echo   "type": "module",
    echo   "scripts": {
    echo     "dev": "vite",
    echo     "build": "vite build",
    echo     "preview": "vite preview"
    echo   },
    echo   "dependencies": {
    echo     "react": "^18.2.0",
    echo     "react-dom": "^18.2.0"
    echo   },
    echo   "devDependencies": {
    echo     "@vitejs/plugin-react": "^4.2.1",
    echo     "vite": "^5.2.0"
    echo   }
    echo } > package.json
)

echo [5/8] Configurando MySQL...
echo    Por favor asegúrate de que MySQL esté instalado y ejecutando
echo    Creando base de datos...
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS conmetal_ot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>nul || echo "⚠️  Ejecuta manualmente: CREATE DATABASE conmetal_ot;"

echo [6/8] Creando archivos de configuración...
cd ..

echo    Creando .env para configuración...
if not exist .env (
    echo # Configuración del proyecto CONMETAL > .env
    echo DB_NAME=conmetal_ot >> .env
    echo DB_USER=root >> .env
    echo DB_PASSWORD= >> .env
    echo DB_HOST=localhost >> .env
    echo DB_PORT=3306 >> .env
    echo DEBUG=True >> .env
)

echo [7/8] Creando scripts de ejecución rápida...
echo    Script para backend...
echo @echo off > run-backend.bat
echo cd backend >> run-backend.bat
echo call venv\Scripts\activate >> run-backend.bat
echo python manage.py runserver >> run-backend.bat

echo    Script para frontend...
echo @echo off > run-frontend.bat
echo cd frontend >> run-frontend.bat
echo npm run dev >> run-frontend.bat

echo [8/8] Instalación completada!
echo.
echo ===============================================
echo    ✅ INSTALACIÓN COMPLETADA EXITOSAMENTE
echo ===============================================
echo.
echo Para ejecutar el sistema:
echo  1. Backend: Ejecuta 'run-backend.bat'
echo  2. Frontend: Ejecuta 'run-frontend.bat'
echo.
echo URLs:
echo  - Frontend: http://localhost:3000
echo  - Backend:  http://localhost:8000
echo  - Admin:    http://localhost:8000/admin
echo.
pause