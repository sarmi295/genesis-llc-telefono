#!/bin/bash
# Script de construcción para Render.com

echo "Iniciando proceso de construcción..."

# Instalar todas las dependencias
pip install -r requirements.txt

# Asegurarse de que existe el directorio static
mkdir -p static

# Verificar que los archivos críticos existen
if [ -f "app.py" ]; then
    echo "✅ app.py encontrado"
else
    echo "❌ app.py no encontrado"
    exit 1
fi

if [ -d "static" ]; then
    echo "✅ Directorio static encontrado"
else
    echo "❌ Directorio static no encontrado"
    exit 1
fi

if [ -f "static/logo_genesis.png" ]; then
    echo "✅ Logo principal encontrado"
else
    echo "⚠️ Logo principal no encontrado, utilizando fallbacks"
fi

echo "Proceso de construcción completado con éxito."
