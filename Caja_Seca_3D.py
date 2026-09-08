import streamlit as st
import plotly.graph_objects as go
import pandas as pd


def main():

    st.title("🚛 Caja seca 3D")

    st.success("Módulo cargado correctamente")

    cantidad = st.slider(
        "Cantidad de pallets",
        1,
        26,
        26
    )
    fig = go.Figure()

    # --------------------------------------------------
    # CONTORNO DE CAJA SECA
    # --------------------------------------------------
    
    largo = 13
    ancho = 2.5
    alto = 2.6
    
    lineas = [
    
        # Piso
        ([0,largo],[0,0],[0,0]),
        ([largo,largo],[0,ancho],[0,0]),
        ([largo,0],[ancho,ancho],[0,0]),
        ([0,0],[ancho,0],[0,0]),
    
        # Techo
        ([0,largo],[0,0],[alto,alto]),
        ([largo,largo],[0,ancho],[alto,alto]),
        ([largo,0],[ancho,ancho],[alto,alto]),
        ([0,0],[ancho,0],[alto,alto]),
    
        # Verticales
        ([0,0],[0,0],[0,alto]),
        ([largo,largo],[0,0],[0,alto]),
        ([largo,largo],[ancho,ancho],[0,alto]),
        ([0,0],[ancho,ancho],[0,alto]),
    ]
    
    for xs, ys, zs in lineas:
    
        fig.add_trace(
            go.Scatter3d(
                x=xs,
                y=ys,
                z=zs,
                mode="lines",
                line=dict(
                    color="black",
                    width=5
                ),
                showlegend=False
            )
        )
    
    # --------------------------------------------------
    # PALLETS
    # --------------------------------------------------
    
    for i in range(cantidad):
    
        fila = 0 if i < 13 else 1
    
        pos = i if i < 13 else i-13
    
        x = pos + 0.5
    
        y = 0.5 if fila == 0 else 1.8
    
        z = 0
    
        fig.add_trace(
            go.Scatter3d(
                x=[x],
                y=[y],
                z=[z],
                mode="markers+text",
                text=[f"{i+1}"],
                textposition="top center",
                marker=dict(
                    size=12,
                    color="red"
                ),
                showlegend=False
            )
        )
    
    fig.update_layout(
    
        height=900,
    
        scene=dict(
    
            xaxis=dict(
                title="Largo",
                range=[0,largo]
            ),
    
            yaxis=dict(
                title="Ancho",
                range=[0,ancho]
            ),
    
            zaxis=dict(
                title="Alto",
                range=[0,alto]
            ),
    
            camera=dict(
                eye=dict(
                    x=1.5,
                    y=1.5,
                    z=0.8
                )
            ),
    
            aspectmode="manual",
    
            aspectratio=dict(
                x=5,
                y=1,
                z=1
            )
        )
    )
    
    st.plotly_chart(
        fig,
        use_container_width=True
    )


    df = pd.DataFrame({
        "Pallet": range(1, cantidad + 1)
    })

    st.dataframe(df)


if __name__ == "__main__":
    main()
