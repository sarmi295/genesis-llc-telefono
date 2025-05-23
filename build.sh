#!/bin/bash
# Script de construcción para Render.com

echo "Iniciando proceso de construcción..."

# Instalar todas las dependencias
if [ -f "requirements-render.txt" ]; then
    echo "✅ Usando requirements-render.txt específico para Render"
    pip install -r requirements-render.txt
else
    echo "✅ Usando requirements.txt estándar"
    pip install -r requirements.txt
fi

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

# Asegurarse de que el logo esté en el directorio static
if [ -f "static/logo_genesis.png" ]; then
    echo "✅ Logo principal encontrado"
else
    echo "⚠️ Logo principal no encontrado, verificando directorio actual..."
    if [ -f "logo_genesis.png" ]; then
        echo "✅ Logo encontrado en el directorio principal, copiando a static/"
        cp logo_genesis.png static/
    else
        echo "⚠️ Usando logo de respaldo"
        if [ -f "static/logo_test.png" ]; then
            echo "✅ Logo de respaldo encontrado"
            cp static/logo_test.png static/logo_genesis.png
        else
            echo "⚠️ Creando un logo de respaldo vacío"
            # Crear un pequeño archivo PNG como respaldo
            echo -n -e "\x89\x50\x4E\x47\x0D\x0A\x1A\x0A\x00\x00\x00\x0D\x49\x48\x44\x52\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1F\xF3\xFF\x61\x00\x00\x00\x01\x73\x52\x47\x42\x00\xAE\xCE\x1C\xE9\x00\x00\x00\x04\x67\x41\x4D\x41\x00\x00\xB1\x8F\x0B\xFC\x61\x05\x00\x00\x00\x09\x70\x48\x59\x73\x00\x00\x0E\xC3\x00\x00\x0E\xC3\x01\xC7\x6F\xA8\x64\x00\x00\x00\x0C\x49\x44\x41\x54\x38\x4F\x63\x60\x18\x05\xA3\x80\x3C\x00\x00\x04\x00\x01\x5A\x94\x93\x60\x00\x00\x00\x00\x49\x45\x4E\x44\xAE\x42\x60\x82" > static/logo_genesis.png
        fi
    fi
fi

# Verificar archivos de respaldo para el logo
if [ -f "encoded_logo.txt" ]; then
    echo "✅ Archivo de logo en base64 encontrado"
else
    echo "⚠️ Creando archivo de logo en base64 de respaldo"
    if [ -f "static/logo_genesis.png" ]; then
        base64 static/logo_genesis.png > encoded_logo.txt
    elif [ -f "static/logo_test.png" ]; then
        base64 static/logo_test.png > encoded_logo.txt
    else
        echo "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAA2hpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuMy1jMDExIDY2LjE0NTY2MSwgMjAxMi8wMi8wNi0xNDo1NjoyNyAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDowMTgwMTE3NDA3MjA2ODExODIyQTlGM0YzNTQxQzc4QiIgeG1wTU06RG9jdW1lbnRJRD0ieG1wLmRpZDo5NzVEOTA1QzQ2MjExMUUyOTM1RUNEMjIxMkZCQkFEQSIgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDo5NzVEOTA1QjQ2MjExMUUyOTM1RUNEMjIxMkZCQkFEQSIgeG1wOkNyZWF0b3JUb29sPSJBZG9iZSBQaG90b3Nob3AgQ1M2IChNYWNpbnRvc2gpIj4gPHhtcE1NOkRlcml2ZWRGcm9tIHN0UmVmOmluc3RhbmNlSUQ9InhtcC5paWQ6MDE4MDExNzQwNzIwNjgxMTgyMkE5RjNGMzU0MUM3OEIiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6MDE4MDExNzQwNzIwNjgxMTgyMkE5RjNGMzU0MUM3OEIiLz4gPC9yZGY6RGVzY3JpcHRpb24+IDwvcmRmOlJERj4gPC94OnhtcG1ldGE+IDw/eHBhY2tldCBlbmQ9InIiPz4ByQffAAAAJ0lEQVR42mL8//8/AyWAiYFCMKgN+P//P85Y+P//f+IoGTDKaAYAwv8GPaBIQ4QAAAAASUVORK5CYII=" > encoded_logo.txt
    fi
fi

echo "Contenido final del directorio static:"
ls -la static/

echo "Proceso de construcción completado con éxito."
