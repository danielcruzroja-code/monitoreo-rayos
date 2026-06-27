import os
import json
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from datetime import datetime
import netCDF4 as nc
import numpy as np

def procesar_glm():
    # Conectarse al servidor público de la NOAA (sin credenciales)
    s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))
    bucket_name = 'noaa-goes16'
    
    # Obtener la fecha actual en UTC
    ahora = datetime.utcnow()
    year = ahora.strftime('%Y')
    day_of_year = ahora.strftime('%j')
    hour = ahora.strftime('%H')
    
    prefix = f"GLM-L2-LCFA/{year}/{day_of_year}/{hour}/"
    
    try:
        # Listar los archivos de la última hora
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        if 'Contents' not in response:
            print("No se encontraron archivos recientes.")
            return
        
        # Tomar el archivo más reciente (el satélite genera uno nuevo cada 20 segundos)
        archivos = sorted(response['Contents'], key=lambda x: x['LastModified'])
        ultimo_archivo = archivos[-1]['Key']
        nombre_local = "temporal_glm.nc"
        
        print(f"Descargando datos de América: {ultimo_archivo}")
        s3.download_file(bucket_name, ultimo_archivo, nombre_local)
        
        # Leer el archivo NetCDF
        ds = nc.Dataset(nombre_local)
        
        # Extraer latitudes y longitudes de todos los rayos
        lats = ds.variables['flash_lat'][:]
        lons = ds.variables['flash_lon'][:]
        
        rayos = []
        for i in range(len(lats)):
            # Al remover el filtro geográfico, abarcamos toda la cobertura del GOES-16 (América completa)
            rayos.append({
                "fecha": ahora.isoformat() + "Z",
                "lat": round(float(lats[i]), 4),
                "lon": round(float(lons[i]), 4),
                "tipo": "total-sat"
            })
        
        ds.close()
        if os.path.exists(nombre_local):
            os.remove(nombre_local)
            
        # Guardar en archivo JSON
        with open('rayos.json', 'w') as f:
            json.dump(rayos, f, indent=2)
        print(f"Procesados {len(rayos)} rayos en toda América exitosamente.")
        
    except Exception as e:
        print(f"Error procesando satélite: {e}")

if __name__ == "__main__":
    procesar_glm()
