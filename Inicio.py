import streamlit as st
import base64

def main():
    # Cargar y codificar la imagen
    def load_image(image_file):
        with open(image_file, "rb") as f:
            data = f.read()
            return base64.b64encode(data).decode()

    # Función para cargar el archivo CSS
    def load_css(file_name):
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    # Cargar el CSS
    load_css('style.css')

    # Ruta del logo
    logo = "IDEAL.jfif"  # Asegúrate de que la ruta sea correcta

    # Cargar y mostrar la imagen en la barra lateral
    st.sidebar.image("OsitoTierno.png", use_column_width=True)  # Asegúrate de que la imagen esté en la misma carpeta

    # Obtener la imagen codificada
    logo_base64 = load_image(logo)

    st.markdown(f"""
            <div style="display: flex; align-items: center;">
                <img src="data:image/jpeg;base64,{logo_base64}" alt="Logo" style="width: 240px; margin-right: 10px;">
                <h1 style="margin-bottom: 0;">Logística: Torre de Monitoreo de Transportación</h1>
            </div>
        """, unsafe_allow_html=True)

    # Contenido adicional
    st.write("Esta es la página principal. Usa el menú de la izquierda para cambiar de página.")

if __name__ == "__main__":
    main()