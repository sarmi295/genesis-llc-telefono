#!/bin/bash
# Script de inicio para Render

# Asegurarnos de que gunicorn esté instalado
pip install gunicorn

# Asegurar que todas las dependencias estén instaladas
pip install -r requirements.txt

# Preparar las carpetas necesarias
mkdir -p static

# Verificar que los archivos de logo existan
echo "Verificando archivos de logo..."
ls -la static/

# Iniciar la aplicación
gunicorn app:app
