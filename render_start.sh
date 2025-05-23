#!/bin/bash
# Script de inicio para Render

# Asegurarnos de que gunicorn esté instalado
pip install gunicorn

# Asegurar que todas las dependencias estén instaladas
if [ -f "requirements-render.txt" ]; then
    echo "✅ Usando requirements-render.txt específico para Render"
    pip install -r requirements-render.txt
else
    echo "✅ Usando requirements.txt estándar"
    pip install -r requirements.txt
fi

# Preparar las carpetas necesarias
mkdir -p static

# Verificar que los archivos de logo existan
echo "Verificando archivos de logo..."
ls -la static/

# Nota: No iniciar gunicorn aquí, Render lo hará con el startCommand
echo "Preparación completada. Render iniciará gunicorn automáticamente."
