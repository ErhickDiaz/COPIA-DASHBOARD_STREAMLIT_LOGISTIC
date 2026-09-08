import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# =========================================================
# MODELO 3D CAJA SECA T1
# Modulo compatible con: from Caja_Seca_3D import main
# =========================================================


def agregar_cubo(fig, x, y, z, largo, ancho, alto, color, nombre, opacidad=0.92):
    """Agrega un paralelepipedo 3D a una figura Plotly."""
    vertices_x = [x, x+largo, x+largo, x, x, x+largo, x+largo, x]
    vertices_y = [y, y, y+ancho, y+ancho, y, y, y+ancho, y+ancho]
    vertices_z = [z, z, z, z, z+alto, z+alto, z+alto, z+alto]

    # Dos triangulos por cada una de las seis caras.
    i = [0, 0, 4, 4, 0, 0, 1, 1, 2, 2, 3, 3]
    j = [1, 2, 5, 6, 1, 5, 2, 6, 3, 7, 0, 4]
    k = [2, 3, 6, 7, 5, 4, 6, 5, 7, 6, 4, 7]

    fig.add_trace(go.Mesh3d(
        x=vertices_x, y=vertices_y, z=vertices_z,
        i=i, j=j, k=k,
        color=color,
        opacity=opacidad,
        flatshading=True,
        name=nombre,
        hovertemplate=f"<b>{nombre}</b><extra></extra>",
        showscale=False,
    ))


def agregar_aristas(fig, x, y, z, largo, ancho, alto, color="#DCE7F3", grosor=2):
    """Dibuja las aristas de un cubo para mejorar la lectura visual."""
    puntos = [
        (x,y,z), (x+largo,y,z), (x+largo,y+ancho,z), (x,y+ancho,z),
        (x,y,z+alto), (x+largo,y,z+alto),
        (x+largo,y+ancho,z+alto), (x,y+ancho,z+alto)
    ]
    segmentos = [
        (0,1),(1,2),(2,3),(3,0),
        (4,5),(5,6),(6,7),(7,4),
        (0,4),(1,5),(2,6),(3,7)
    ]
    for a,b in segmentos:
        fig.add_trace(go.Scatter3d(
            x=[puntos[a][0], puntos[b][0]],
            y=[puntos[a][1], puntos[b][1]],
            z=[puntos[a][2], puntos[b][2]],
            mode="lines",
            line=dict(color=color, width=grosor),
            hoverinfo="skip",
            showlegend=False,
        ))


def construir_layout_pallets(
    cantidad=26,
    largo_caja=16.0,
    ancho_caja=2.45,
    alto_caja=2.70,
    largo_pallet=1.20,
    ancho_pallet=1.00,
    alto_pallet=1.45,
    separacion=0.025,
):
    """Genera posiciones fijas en dos filas, con hasta 13 pallets por fila."""
    cantidad = max(1, min(int(cantidad), 26))
    posiciones = []
    por_fila = 13

    # Centrado transversal dentro de la caja.
    ancho_carga = 2 * ancho_pallet + separacion
    margen_y = max((ancho_caja - ancho_carga) / 2, 0)

    # Centrado longitudinal del bloque completo de 13 posiciones.
    largo_carga = por_fila * largo_pallet + (por_fila - 1) * separacion
    margen_x = max((largo_caja - largo_carga) / 2, 0)

    for numero in range(1, cantidad + 1):
        fila = 0 if numero <= por_fila else 1
        posicion_fila = numero - 1 if fila == 0 else numero - por_fila - 1
        x = margen_x + posicion_fila * (largo_pallet + separacion)
        y = margen_y + fila * (ancho_pallet + separacion)
        posiciones.append({
            "Pallet": numero,
            "Fila": "Izquierda" if fila == 0 else "Derecha",
            "Posicion": posicion_fila + 1,
            "X": round(x, 3),
            "Y": round(y, 3),
            "Z": 0.0,
            "Largo": largo_pallet,
            "Ancho": ancho_pallet,
            "Alto": alto_pallet,
        })

    advertencias = []
    if largo_carga > largo_caja:
        advertencias.append("El largo configurado de los pallets excede el largo interior de la caja.")
    if ancho_carga > ancho_caja:
        advertencias.append("El ancho configurado de las dos filas excede el ancho interior de la caja.")
    if alto_pallet > alto_caja:
        advertencias.append("La altura configurada del pallet excede la altura interior de la caja.")

    return pd.DataFrame(posiciones), advertencias


def crear_figura_3d(df, largo_caja, ancho_caja, alto_caja, pallet_seleccionado=None):
    fig = go.Figure()

    # Piso semitransparente de la caja.
    agregar_cubo(
        fig, 0, 0, -0.03,
        largo_caja, ancho_caja, 0.03,
        color="#334155", nombre="Piso caja seca", opacidad=0.40
    )
    agregar_aristas(fig, 0, 0, 0, largo_caja, ancho_caja, alto_caja,
                    color="#94A3B8", grosor=3)

    colores = {"Izquierda": "#00C2A8", "Derecha": "#3B82F6"}

    for _, r in df.iterrows():
        seleccionado = pallet_seleccionado == int(r["Pallet"])
        color = "#F59E0B" if seleccionado else colores[r["Fila"]]
        nombre = (
            f"Pallet {int(r['Pallet'])} | {r['Fila']} | "
            f"Posicion {int(r['Posicion'])}"
        )
        agregar_cubo(
            fig,
            r["X"], r["Y"], r["Z"],
            r["Largo"], r["Ancho"], r["Alto"],
            color=color, nombre=nombre, opacidad=0.95
        )
        agregar_aristas(
            fig,
            r["X"], r["Y"], r["Z"],
            r["Largo"], r["Ancho"], r["Alto"],
            color="#08111F", grosor=2
        )
        fig.add_trace(go.Scatter3d(
            x=[r["X"] + r["Largo"]/2],
            y=[r["Y"] + r["Ancho"]/2],
            z=[r["Z"] + r["Alto"] + 0.05],
            mode="text",
            text=[str(int(r["Pallet"]))],
            textfont=dict(color="#FFFFFF", size=10),
            hoverinfo="skip",
            showlegend=False,
        ))

    fig.update_layout(
        height=720,
        margin=dict(l=0, r=0, t=35, b=0),
        paper_bgcolor="#07111F",
        plot_bgcolor="#07111F",
        font=dict(color="#E5EDF5"),
        scene=dict(
            bgcolor="#07111F",
            xaxis=dict(title="Largo (m)", range=[0, largo_caja], gridcolor="#1E3A52"),
            yaxis=dict(title="Ancho (m)", range=[0, ancho_caja], gridcolor="#1E3A52"),
            zaxis=dict(title="Alto (m)", range=[0, alto_caja], gridcolor="#1E3A52"),
            aspectmode="manual",
            aspectratio=dict(x=4.8, y=1.0, z=1.0),
            camera=dict(eye=dict(x=1.55, y=1.55, z=1.15)),
        ),
        showlegend=False,
        title="Modelo 3D de caja seca y posiciones de pallets",
    )
    return fig


def main():
    st.title("🚛 Caja seca 3D · 26 pallets")
    st.caption(
        "MVP visual para validar el acomodo 13 + 13. Las dimensiones son "
        "parametrizables y deben ajustarse a la ficha tecnica real del equipo y pallet."
    )

    with st.sidebar:
        st.header("⚙️ Configuración 3D")
        cantidad = st.slider("Pallets enviados", 1, 26, 26)
        largo_caja = st.number_input("Largo interior caja (m)", 10.0, 20.0, 16.0, 0.05)
        ancho_caja = st.number_input("Ancho interior caja (m)", 2.0, 3.0, 2.45, 0.01)
        alto_caja = st.number_input("Alto interior caja (m)", 2.0, 3.5, 2.70, 0.01)
        st.divider()
        largo_pallet = st.number_input("Largo pallet (m)", 0.5, 1.5, 1.20, 0.01)
        ancho_pallet = st.number_input("Ancho pallet (m)", 0.5, 1.5, 1.00, 0.01)
        alto_pallet = st.number_input("Alto carga pallet (m)", 0.2, 2.8, 1.45, 0.05)
        separacion = st.number_input("Separación entre pallets (m)", 0.0, 0.20, 0.025, 0.005)

    df, advertencias = construir_layout_pallets(
        cantidad, largo_caja, ancho_caja, alto_caja,
        largo_pallet, ancho_pallet, alto_pallet, separacion
    )

    pallet_sel = st.selectbox(
        "Resaltar pallet",
        ["Ninguno"] + df["Pallet"].astype(int).tolist()
    )
    pallet_sel = None if pallet_sel == "Ninguno" else int(pallet_sel)

    volumen_caja = largo_caja * ancho_caja * alto_caja
    volumen_carga = (largo_pallet * ancho_pallet * alto_pallet) * cantidad
    ocupacion_vol = volumen_carga / volumen_caja if volumen_caja else 0
    ocupacion_puestos = cantidad / 26

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pallets", f"{cantidad}/26")
    c2.metric("Ocupación de posiciones", f"{ocupacion_puestos:.1%}")
    c3.metric("Volumen geométrico carga", f"{volumen_carga:.2f} m³")
    c4.metric("Ocupación volumétrica", f"{ocupacion_vol:.1%}")

    for aviso in advertencias:
        st.error(aviso)

    fig = crear_figura_3d(
        df, largo_caja, ancho_caja, alto_caja,
        pallet_seleccionado=pallet_sel
    )
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

    with st.expander("📋 Ver coordenadas y dimensiones"):
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.info(
        "Este MVP representa 26 posiciones fijas, 13 por lado. No calcula todavía "
        "restricciones de peso por eje, estabilidad, secuencia de descarga ni "
        "compatibilidad física entre productos."
    )


if __name__ == "__main__":
    main()
