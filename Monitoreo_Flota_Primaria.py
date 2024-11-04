import streamlit as st
import mygeotab
from datetime import datetime, timedelta
import time
import requests
import os
from shareplum import Site
from shareplum.site import Version
from shareplum import Office365
import pandas as pd
import re
import base64
from io import StringIO, BytesIO

def main():

        # Crear DataFrame para el histórico
    historico_columnas = ['Vehículo', 'ID', 'Hora en Partida', 'Hora en Transito', 'Hora en Destino', 'Fecha']
    historico_df = pd.DataFrame(columns=historico_columnas)

    # Función para convertir distancia en texto a kilómetros
    def convertir_distancia_a_km(distancia):
        # Asume que la distancia es una cadena en formato como '10 km' o '200 m'
        if 'km' in distancia:
            return float(distancia.replace(' km', ''))  # Mantener la distancia en kilómetros
        elif 'm' in distancia:
            return float(distancia.replace(' m', '')) / 1000  # Convertir metros a kilómetros
        return None

    # Función para cargar el archivo CSS
    def load_css(file_name):
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

        # Cargar y codificar la imagen
    def load_image(image_file):
        with open(image_file, "rb") as f:
            data = f.read()
            return base64.b64encode(data).decode()
        
    # Cargar el CSS
    load_css('style.css')

    # Cargar y mostrar la imagen en la barra lateral
    st.sidebar.image("OsitoTierno.png", use_column_width=True)  # Asegúrate de que la imagen esté en la misma carpeta

    # Título de la página

    # Conéctate a la base de datos de Geotab usando tus credenciales
    username = st.secrets["username"]
    password = st.secrets["Soporte.2024"]
    password2 = st.secrets["Soporte.2028"]
    database = st.secrets["database"]
    api_key = st.secrets["api_key"]
    mode = 'driving'  # Modo de transporte

    # URL de SharePoint y la carpeta destino
    sharepoint_url = 'https://gbconnect.sharepoint.com'  # URL corregida de SharePoint
    site_url = '/sites/Torredetransportacin'  # URL del sitio de SharePoint
    folder_url = 'Documentos compartidos/Transportación Primaria'  # Carpeta en SharePoint

    destinos_coordenadas = {
        "LO ESPEJO": {"latitud": -33.536206, "longitud": -70.694935},
        "VIÑA DEL MAR": {"latitud": -33.1361809, "longitud": -71.5560586},
        "CEDIS":{"latitud": -33.324003, "longitud": -70.712268},
        "EL PINAR":{"latitud":-33.491674, "longitud": -70.627633},
        "TALAGANTE":{"latitud":-33.674750,"longitud":-70.951093},
        "MELIPILLA":{"latitud":-33.678339,"longitud":-71.229487},
        "RANCAGUA":{"latitud":-34.162651,"longitud":-70.727089},
        "LOS ANDES":{"latitud":-34.162651,"longitud":-70.727089}
    }

    # Autenticación en Office 365 y conexión con SharePoint
    authcookie = Office365(sharepoint_url, username=username, password=password2).GetCookies()

    # Conectar al sitio de SharePoint
    site = Site(sharepoint_url + site_url, version=Version.v365, authcookie=authcookie)

    # Acceder a la carpeta en SharePoint
    folder = site.Folder(folder_url)

    # Descargar el primer archivo desde la carpeta de SharePoint
    file = folder.get_file('Template de programación_Geotab.xlsx')
    file2 = folder.get_file("Histórico Viajes Primaria.xlsx")

    Programa_rutas = pd.read_excel(file)
    historico_df = pd.read_excel(file2)

    print(Programa_rutas)

    # Autenticación y creación de la conexión a la API de Geotab
    api = mygeotab.API(username=username, password=password, database=database)
    api.authenticate()

    # Función para obtener las coordenadas de un vehículo y su nombre
    def get_vehicle_coordinates(vehicle_id):
        try:
            # Definir el rango de fechas para la búsqueda
            to_date = datetime.utcnow()
            from_date = datetime.utcnow()

            # Obtener los registros de log (LogRecord) para el vehículo
            log_records = api.get("LogRecord", search={
                "deviceSearch": {"id": vehicle_id},
                "fromDate": from_date.isoformat(),
                "toDate": to_date.isoformat(),
                "resultsLimit": 1000  # Limitar a 1000 resultados para la paginación
            })

            # Obtener el vehículo y su nombre desde la API
            vehicle = api.get("Device", search={"id": vehicle_id})[0]
            vehicle_name = vehicle.get("name")

            # Si hay registros, tomar el último
            if log_records:
                latest_record = log_records[-1]  # Obtener el último registro
                latitude = latest_record.get("latitude")
                longitude = latest_record.get("longitude")
                return {"name": vehicle_name,"ID":vehicle_id, "latitude": latitude, "longitude": longitude}
            else:
                return {"name": vehicle_name,"ID":vehicle_id, "latitude": None, "longitude": None}
        except Exception as e:
            print(f"Error al obtener las coordenadas del vehículo {vehicle_id}: {e}")
            return {"name": None,"ID": None ,"latitude": None, "longitude": None}

    # Función para obtener la distancia y duración utilizando la API de Google Directions
    def get_route_data(origin_lat, origin_lng, dest_lat, dest_lng):
        url = f'https://maps.googleapis.com/maps/api/directions/json?origin={origin_lat},{origin_lng}&destination={dest_lat},{dest_lng}&mode={mode}&key={api_key}'
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            if data['routes']:
                route = data['routes'][0]['legs'][0]
                duration = route['duration']['text']
                distance = route['distance']['text']
                return {"distance": distance, "duration": duration}
            else:
                return {"distance": None, "duration": None}
        else:
            print(f"Error en la solicitud: {response.status_code}")
            return {"distance": None, "duration": None}

    # Función para convertir el texto de duración en minutos (si es necesario)
    def duration_to_minutes(duration):
        # Utilizar expresiones regulares para extraer horas y minutos
        hours = re.search(r'(\d+)\s*hour', duration)
        minutes = re.search(r'(\d+)\s*min', duration)
        
        # Convertir horas y minutos en enteros
        total_minutes = 0
        if hours:
            total_minutes += int(hours.group(1)) * 60  # 1 hora = 60 minutos
        if minutes:
            total_minutes += int(minutes.group(1))
        
        return total_minutes

    # Agregar columnas vacías para la distancia y duración en el DataFrame
    Programa_rutas['Distancia'] = None
    Programa_rutas["Estado"] = None
    Programa_rutas["Hora Salida Real"] = None
    Programa_rutas["Hora Llegada Real"] = None

    print(datetime.now())
    # Recorrer los vehículos del DataFrame y calcular la ruta hacia el destino

    # Recorrer los vehículos del DataFrame y calcular la ruta hacia el destino
    for index, row in Programa_rutas.iterrows():
        vehicle_name = row['Vehículo']
        destino = row['Destino']
        vehicle_id = row["ID"]
        
        # Obtener las coordenadas del destino
        destino_coords = destinos_coordenadas.get(destino)
        dest_lat = destino_coords['latitud']
        dest_lng = destino_coords['longitud']
        
        # Obtener las coordenadas actuales del vehículo
        vehicle_data = get_vehicle_coordinates(vehicle_id)
        origin_lat = vehicle_data['latitude']
        origin_lng = vehicle_data['longitude']
    
        # Si se tienen ambas coordenadas, solicitar la ruta
        if origin_lat is not None and origin_lng is not None:
            # Obtener los datos de la ruta desde Google Maps API
            route_data = get_route_data(origin_lat, origin_lng, dest_lat, dest_lng)
            distancia_texto = route_data['distance']
            duracion_texto = route_data['duration']

            # Convertir la distancia a kilómetros
            distancia_a_destino = convertir_distancia_a_km(distancia_texto)

             # Actualizar las columnas de distancia y duración
            Programa_rutas.at[index, 'Distancia'] = route_data['distance']
            Programa_rutas.at[index, 'Tiempo Restante'] = route_data['duration']
            #Programa_rutas = Programa_rutas.drop(columns=['Duration'])
            # Calcular la "Hora llegada Real"
            if route_data['duration']:  # Verificar si 'duration' no es None
                minutes_to_add = duration_to_minutes(route_data['duration'])
                hora_llegada_real = datetime.now() + timedelta(minutes=minutes_to_add)
                Programa_rutas.at[index, "Hora Llegada Real"] = hora_llegada_real
            else:
                Programa_rutas.at[index, "Hora Llegada Real"] = None

            # Actualizar el estado del camión basado en la distancia (0.2 km)
            if distancia_a_destino is not None:
                if distancia_a_destino < 0.3:  # Si la distancia es menor a 0.3 km
                    # Vehículo en destino
                    Programa_rutas.at[index, 'Estado'] = "En destino"
                    Programa_rutas.at[index, 'Hora Llegada Real'] = datetime.now()
                
                elif distancia_a_destino > 0.3:
                    # Vehículo en tránsito
                    Programa_rutas.at[index, 'Estado'] = "En transito"
                    Programa_rutas.at[index, 'Hora Salida Real'] = datetime.now()

                print(f"Vehículo: {vehicle_name}, Estado: {Programa_rutas.at[index, 'Estado']}")

            if Programa_rutas.at[index,'Estado'] == "En destino":

                # Mover la información al archivo histórico
                nuevo_registro_historico = {
                    'Fecha': datetime.now().date(),
                    'Vehículo': vehicle_name,
                    'ID': vehicle_id,
                    "Salida": Programa_rutas.at[index,"Salida"],
                    "Destino": Programa_rutas.at[index,"Destino"],
                    'Hora en Transito': row['Hora Salida Real'],
                    'Hora Llegada Real': row['Hora Llegada Real'],
                }

                nuevo_registro_historico_df = pd.DataFrame([nuevo_registro_historico])

                # Concatenar el nuevo registro con el DataFrame histórico
                historico_df = pd.concat([historico_df, nuevo_registro_historico_df], ignore_index=True)

                historical_data_file = "Histórico Viajes Primaria.xlsx"

                # Guardar el DataFrame actualizado directamente en SharePoint
                output = StringIO()
                historico_df.to_excel(output, index=False)
                folder.upload_file(output.getvalue(), historical_data_file)

                print(f"Archivo '{historical_data_file}' subido exitosamente a SharePoint.")

                # Eliminar el vehículo de la base de datos
                Programa_rutas.drop(index, inplace=True)

        else:
            print(f"No se pudieron obtener las coordenadas del vehículo {vehicle_name} (ID: {vehicle_id}).")

    # Mostrar el DataFrame actualizado con las nuevas columnas

    template_programacion = "Template de programación_Geotab.xlsx"

    output = BytesIO()
    Programa_rutas.to_excel(output, index=False)
    folder.upload_file(output.getvalue(), template_programacion)

    print(f"Archivo '{template_programacion}' subido exitosamente a SharePoint.")
        
    # Ruta del logo
    logo = "IDEAL.jfif"  # Asegúrate de que la ruta sea correcta
    # Obtener la imagen codificada

    logo_base64 = load_image(logo)

    st.markdown(f"""
            <div style="display: flex; align-items: center;">
                <img src="data:image/jpeg;base64,{logo_base64}" alt="Logo" style="width: 240px; margin-right: 10px;">
                <h1 style="margin-bottom: 0;">Logística: Monitoreo transportación primaria.</h1>
            </div>
        """, unsafe_allow_html=True)
    
    st.write("")
    st.write("")
    st.write("")
    
    st.markdown(
        """
        <style>
        .blue-header table {
            width: 100%;
            border-collapse: collapse;
        }
        .blue-header thead tr th {
            background-color: #1C306A;
            color: white;
            padding: 10px;
        }
        .blue-header tbody tr td {
            text-align: center;
            padding: 10px;
            font-weight: bold;  /* Negrita */
        }
        </style>
        """, unsafe_allow_html=True
    )

    # Convertir el DataFrame a HTML con estilo personalizado
    st.markdown(Programa_rutas.style.set_table_attributes('class="blue-header"').to_html(), unsafe_allow_html=True)
    
if __name__ == "__main__":
    main()
