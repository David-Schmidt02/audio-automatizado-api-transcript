#!/bin/bash

# Este script copia los archivos WAV desde un contenedor Docker a tu host local

# Obtener el ID del contenedor en ejecución
CONTAINER_ID=$(docker ps -q -f ancestor=soflex-desktop)

if [ -z "$CONTAINER_ID" ]; then
    echo "Error: No se encontró ningún contenedor en ejecución con la imagen soflex-desktop"
    exit 1
fi

# Crear directorio de destino si no existe
DEST_DIR="./wavs_descargados"
mkdir -p "$DEST_DIR"

# Copiar todos los archivos WAV
echo "Copiando archivos WAV desde el contenedor $CONTAINER_ID..."
docker cp $CONTAINER_ID:/home/soflex/data/records "$DEST_DIR"

echo "Archivos WAV copiados a $DEST_DIR"
echo "Listado de archivos:"
find "$DEST_DIR" -name "*.wav" | sort
