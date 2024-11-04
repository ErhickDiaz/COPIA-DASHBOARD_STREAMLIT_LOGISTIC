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

if __name__ == "__main__":
    main()