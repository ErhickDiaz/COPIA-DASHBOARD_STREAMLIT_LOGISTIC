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

    x = []
    y = []
    z = []
    texto = []

    for i in range(cantidad):

        fila = 0 if i < 13 else 1
        posicion = i if i < 13 else i - 13

        x.append(posicion)
        y.append(fila)
        z.append(0)

        texto.append(
            f"Pallet {i+1}"
        )

    fig.add_trace(
        go.Scatter3d(
            x=x,
            y=y,
            z=z,
            mode="markers+text",
            text=texto,
            marker=dict(
                size=10,
                color="red"
            )
        )
    )

    fig.update_layout(
        height=700,
        scene=dict(
            xaxis_title="Largo",
            yaxis_title="Ancho",
            zaxis_title="Altura"
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
