import os
import json
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from datetime import datetime, timedelta
import netCDF4 as nc
import numpy as np

def intentar_descarga(s3, bucket_name, tiempo):
    year = tiempo.strftime('%Y')
    day_of_year = tiempo.strftime('%j')
    hour = tiempo.strftime('%H')
    prefix = f"GLM-L2-LCFA/{year}/{day_of_year}/{hour}/"
    
    print(f"Buscando archivos en la ruta: {prefix}")
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    
    if 'Contents' in response:
        # Filtrar solo archivos con la extensión .nc correctos
        archivos = [x for x in response['Contents'] if x['Key'].endswith('.nc')]
        if archivos:
            # Ordenar por el más reciente
            archivos_ordenados = sorted(archivos, key=lambda x: x['LastModified'])
            return archivos_ordenados[-1]['Key']
    return None

def procesar_glm():
    s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))
    bucket_name = 'noaa-goes16'
    
    # Intentar con la hora actual UTC
    ahora = datetime.utcnow()
    ultimo_archivo = intentar_descarga(s3, bucket_name, ahora)
    
    # Si no hay archivos todavía (cambio de hora o desfase), intentar con 10 minutos atrás
    if not ultimo_archivo:
        print("Desfase detectado. Intentando buscar en el bloque de tiempo anterior...")
        hace_diez_min = ahora - timedelta(minutes=10)
        ultimo_archivo = intentar_descarga(s3, bucket_name, hace_diez_min)
        
    if not ultimo_archivo:
        print("No se encontraron archivos en la NOAA para este bloque de tiempo.")
        return

    nombre_local = "temporal_glm.nc"
    try:
        print(f"Descargando datos del satélite: {ultimo_archivo}")
        s3.download_file(bucket_name, ultimo_archivo, nombre_local)
        
        # Leer el archivo NetCDF
        ds = nc.Dataset(nombre_local)
        
        lats = ds.variables['flash_lat'][:]
        lons = ds.variables['flash_lon'][:]
        
        rayos = []
        for i in range(len(lats)):
            rayos.append({
                "fecha": ahora.isoformat() + "Z",
                "lat": round(float(lats[i]), 4),
                "lon": round(float(lons[i]), 4),
                "tipo": "total-sat"
            })
        
        ds.close()
        if os.path.exists(nombre_local):
            os.remove(nombre_local)
            
        # Guardar SÍ O SÍ el archivo, si no hay rayos guardamos un registro de prueba
        if len(rayos) == 0:
            print("Cero rayos detectados en este instante. Insertando punto de control.")
            rayos.append({
                "fecha": ahora.isoformat() + "Z",
                "lat": 20.674,
                "lon": -103.346,
                "tipo": "test-control"
            })
            
        with open('rayos.json', 'w') as f:
            json.dump(rayos, f, indent=2)
        print(f"Procesados {len(rayos)} puntos exitosamente.")
        
    except Exception as e:
        print(f"Error procesando satélite: {e}")

if __name__ == "__main__":
    procesar_glm()
