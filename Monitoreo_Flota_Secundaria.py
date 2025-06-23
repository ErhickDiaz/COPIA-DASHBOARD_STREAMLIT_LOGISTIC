import streamlit as st

def main(): 
    # Función para cargar el archivo CSS
    def load_css(file_name):
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    # Cargar el CSS
    load_css('style.css')
    
    # Cargar y mostrar la imagen en la barra lateral
    st.sidebar.image("OsitoTierno.png", use_column_width=True)  # Asegúrate de que la imagen esté en la misma carpeta

    # Título de la página
    st.title("Página 3")

    st.write("¡Bienvenido a la Página 3!")
    st.write("Aquí puedes agregar otros datos o funcionalidades.")

import streamlit as st
import requests
import pandas as pd
import datetime
import os
 
# Autorefresh cada 15 min (900,000 ms)
st.experimental_rerun() if st.experimental_get_query_params().get("refresh") else st.experimental_set_query_params(refresh="1")
st_autorefresh = st.experimental_data_editor.__globals__["st_autorefresh"]
st_autorefresh(interval=900000, key="alert-refresh")  # 15 minutos
 
# Configuración de la API
UUID = "daaf3640-0c6e-4adb-80d6-8fcb53ddce23"
API_KEY = "41278250-0edf-41e5-aef7-3ec5342563bd"
ENDPOINT = "https://external.driv.in/api/external/v2/stop_events"
HEADERS = {
    "X-API-Key": API_KEY,
    "X-UUID": UUID
}
 
# Parámetros
TIEMPO_LIMITE_MIN = 90
HORARIO_INICIO = 7
HORARIO_FIN = 17
DIAS_VALIDOS = set([0, 1, 2, 3, 4, 5])  # Lunes a sábado
ARCHIVO_EXCEL = "historico_alertas_tiempo_espera.xlsx"
 
# Función para obtener y filtrar datos
def obtener_alertas():
    hoy = datetime.datetime.now().date().isoformat()
    params = {"start_date": hoy, "end_date": hoy}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
 
    if response.status_code != 200:
        return f"Error {response.status_code}", pd.DataFrame()
 
    data = response.json()
    df = pd.DataFrame(data)
 
    if df.empty or "service_time" not in df.columns:
        return "Sin datos o estructura inválida", pd.DataFrame()
 
    df_filtrado = df[df["service_time"] > TIEMPO_LIMITE_MIN].copy()
    return None, df_filtrado
 
# Interfaz de la app
st.title("🚨 Alertas por Tiempo de Espera > 90 min")
 
# Validación de horario
ahora = datetime.datetime.now()
dentro_horario = (
    ahora.weekday() in DIAS_VALIDOS and
    HORARIO_INICIO <= ahora.hour < HORARIO_FIN
)
 
if dentro_horario:
    error, df_alertas = obtener_alertas()
    if error:
        st.error(error)
    elif not df_alertas.empty:
        st.warning(f"🚛 {len(df_alertas)} camión(es) con espera > 90 minutos:")
        st.dataframe(df_alertas[["vehicle_license_plate", "location_name", "service_time", "stop_start_date", "stop_end_date"]])
 
        # Guardar en Excel con timestamp
        df_alertas["registro_alerta"] = ahora.strftime("%Y-%m-%d %H:%M:%S")
 
        if os.path.exists(ARCHIVO_EXCEL):
            historico = pd.read_excel(ARCHIVO_EXCEL)
            historico = pd.concat([historico, df_alertas], ignore_index=True)
        else:
            historico = df_alertas
 
        historico.to_excel(ARCHIVO_EXCEL, index=False)
    else:
        st.success("✅ No hay camiones con espera excesiva en este momento.")
else:
    st.info("⏱️ Fuera del horario de monitoreo (Lun-Sáb, 07:00 a 17:00).")

if __name__ == "__main__":
    main()
