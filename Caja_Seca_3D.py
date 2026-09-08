import streamlit as st
import plotly.graph_objects as go
import pandas as pd


def dibujar_caja_3d(fig, x0, x1, y0, y1, z0, z1, color="red", ancho_linea=4):
    """Dibuja el contorno (wireframe) de una caja/pallet en 3D."""
    aristas = [
        ([x0, x1], [y0, y0], [z0, z0]),
        ([x1, x1], [y0, y1], [z0, z0]),
        ([x1, x0], [y1, y1], [z0, z0]),
        ([x0, x0], [y1, y0], [z0, z0]),

        ([x0, x1], [y0, y0], [z1, z1]),
        ([x1, x1], [y0, y1], [z1, z1]),
        ([x1, x0], [y1, y1], [z1, z1]),
        ([x0, x0], [y1, y0], [z1, z1]),

        ([x0, x0], [y0, y0], [z0, z1]),
        ([x1, x1], [y0, y0], [z0, z1]),
        ([x1, x1], [y1, y1], [z0, z1]),
        ([x0, x0], [y1, y1], [z0, z1]),
    ]

    for xs, ys, zs in aristas:
        fig.add_trace(
            go.Scatter3d(
                x=xs, y=ys, z=zs,
                mode="lines",
                line=dict(color=color, width=ancho_linea),
                showlegend=False,
                hoverinfo="skip",
            )
        )


def main():
    st.title("🚛 Caja seca 3D")
    st.success("Módulo cargado correctamente")

    # --------------------------------------------------
    # DIMENSIONES DE LA CAJA SECA (m)
    # --------------------------------------------------
    largo = 13.0
    ancho = 2.5
    alto = 2.6

    # --------------------------------------------------
    # DIMENSIONES DEL PALLET (m) -- ajusta a tu pallet real
    # --------------------------------------------------
    pallet_largo = 1.0
    pallet_ancho = 1.1
    pallet_alto = st.slider("Altura de carga por pallet (m)", 0.5, 2.2, 1.5, 0.1)

    max_por_fila = int(largo // pallet_largo)
    cantidad_max = max_por_fila * 2

    cantidad = st.slider("Cantidad de pallets", 1, cantidad_max, cantidad_max)

    fig = go.Figure()

    # Contorno de la caja seca
    dibujar_caja_3d(fig, 0, largo, 0, ancho, 0, alto, color="black", ancho_linea=5)

    # --------------------------------------------------
    # PALLETS COMO VOLUMENES REALES
    # --------------------------------------------------
    datos_pallets = []

    for i in range(cantidad):
        fila = 0 if i < max_por_fila else 1
        pos = i if i < max_por_fila else i - max_por_fila

        x0 = pos * pallet_largo
        x1 = x0 + pallet_largo

        y0 = 0.05 if fila == 0 else ancho - pallet_ancho - 0.05
        y1 = y0 + pallet_ancho

        z0 = 0
        z1 = pallet_alto

        color = "crimson" if fila == 0 else "royalblue"

        dibujar_caja_3d(fig, x0, x1, y0, y1, z0, z1, color=color, ancho_linea=3)

        fig.add_trace(
            go.Scatter3d(
                x=[(x0 + x1) / 2],
                y=[(y0 + y1) / 2],
                z=[z1],
                mode="text",
                text=[f"{i+1}"],
                textposition="top center",
                showlegend=False,
            )
        )

        datos_pallets.append({
            "Pallet": i + 1,
            "Fila": fila + 1,
            "X (m)": round(x0, 2),
            "Y (m)": round(y0, 2),
            "Alto carga (m)": pallet_alto,
        })

    fig.update_layout(
        height=900,
        scene=dict(
            xaxis=dict(title="Largo (m)", range=[0, largo]),
            yaxis=dict(title="Ancho (m)", range=[0, ancho]),
            zaxis=dict(title="Alto (m)", range=[0, alto]),
            camera=dict(eye=dict(x=1.5, y=1.5, z=0.8)),
            aspectmode="manual",
            aspectratio=dict(x=5, y=1, z=1),
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

    df = pd.DataFrame(datos_pallets)
    st.dataframe(df)


if __name__ == "__main__":
    main()
