import streamlit as st
from Inicio import main as inicio_main
from Monitoreo_Pre_Primaria import main as pre_primaria_main
from Monitoreo_Flota_Primaria import main as flota_primaria_main
from Monitoreo_Flota_Secundaria import main as flota_secundaria_main
from streamlit_autorefresh import st_autorefresh
import time

st.set_page_config(layout="wide")

# Estilos CSS para los botones
st.markdown(
    """
    <style>
    /* Estilo para los botones de la barra lateral */
    .stButton > button {
        background-color: #1C306A; /* Color de fondo */
        color: white; /* Color del texto */
        padding: 10px 20px;
        margin: 5px;
        margin-left: 30px; /* Ajusta este valor para mover el botón a la derecha */
        border-radius: 5px;
        font-weight: bold;
        border: none; /* Elimina el borde */
        cursor: pointer; /* Cambia el cursor al pasar el mouse */
    }
    .stButton > button:hover {
        background-color: #E62530; /* Color al pasar el mouse */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Inicializar el estado de la sesión si no existe
if 'selection' not in st.session_state:
    st.session_state.selection = "Inicio"  # Valor predeterminado

def main():
    st.sidebar.title("📑 Menú de Navegación")

    options = {
        "Inicio": "🏠",
        "Monitoreo Pre Primaria": "📊",
        "Monitoreo Flota Primaria": "🚚",
        "Monitoreo Flota Secundaria": "🚛"
    }

    for option, icon in options.items():
        if st.sidebar.button(f"{icon} {option}"):
            st.session_state.selection = option  # Guardar la selección en session_state

    # Establecer la frecuencia de actualización solo en la página seleccionada
    st_autorefresh(interval=180000, key="page_refresh")  # Intervalo en milisegundos (3 minutos)

    # Lógica de navegación
    if st.session_state.selection == "Inicio":
        inicio_main()
    elif st.session_state.selection == "Monitoreo Pre Primaria":
        pre_primaria_main()
    elif st.session_state.selection == "Monitoreo Flota Primaria":
        flota_primaria_main()
    elif st.session_state.selection == "Monitoreo Flota Secundaria":
        flota_secundaria_main()

if __name__ == "__main__":
    main()

   
