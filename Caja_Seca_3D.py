from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------
# CARGA Y LIMPIEZA DE DATOS (export WMS: LPN por carga)
# --------------------------------------------------------------------

RUTA_DATA = Path("data")

COLUMNAS_UTILES = [
    "Nro Carga", "Nro LPN", "Codigo", "Descripción de artículo",
    "Cant. Empacada", "Peso", "Volum", "Tipo",
]


def _arreglar_encoding(texto):
    """El export viene con doble-encoding UTF-8 -> Latin-1 en tildes/ñ."""
    if not isinstance(texto, str):
        return texto
    try:
        return texto.encode("latin1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return texto


def _limpiar_valor(valor):
    """Excel exporta ids/numeros como ="1234" para no perder ceros a la izquierda."""
    if isinstance(valor, str) and valor.startswith('="'):
        valor = valor[2:]
        if valor.endswith('"'):
            valor = valor[:-1]
    return valor


def _obtener_archivo_entrada():
    if RUTA_DATA.exists():
        csvs = sorted(RUTA_DATA.glob("oblpnCLIDtmpojn6m9fp.csv"))
        if len(csvs) == 1:
            return csvs[0]
        if len(csvs) > 1:
            nombre = st.selectbox("Archivo en data/", [c.name for c in csvs])
            return RUTA_DATA / nombre
    return st.file_uploader("Sube el CSV de LPN por carga", type="csv")


@st.cache_data
def cargar_detalle(archivo) -> pd.DataFrame:
    df = pd.read_csv(archivo, sep=";", dtype=str)
    df.columns = [_arreglar_encoding(c) for c in df.columns]
    df = df[COLUMNAS_UTILES].copy()

    for col in df.columns:
        df[col] = df[col].map(_limpiar_valor).map(_arreglar_encoding)

    for col in ["Cant. Empacada", "Peso", "Volum"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


@st.cache_data
def construir_pallets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Colapsa el detalle (1 fila por producto dentro del pallet) a 1 fila por LPN.

    OJO -- validado con el archivo real:
    - Peso y Volum vienen IDENTICOS en todas las lineas de un mismo LPN (son
      atributos del pallet, no del producto). Por eso se usa 'first', nunca 'sum'.
    - Cant. Empacada si es por linea de producto, por eso esa se suma.
    """
    pallets = df.groupby("Nro LPN").agg(
        nro_carga=("Nro Carga", "first"),
        tipo=("Tipo", "first"),
        n_codigos=("Codigo", "nunique"),
        codigos=("Codigo", lambda s: ", ".join(sorted(set(s)))),
        cajas=("Cant. Empacada", "sum"),
        peso_g=("Peso", "first"),
        volumen_m3=("Volum", "first"),
    ).reset_index().rename(columns={"Nro LPN": "lpn"})

    pallets["peso_kg"] = pallets["peso_g"] / 1000
    pallets["anomalia_full"] = (pallets["tipo"] == "FULL-CONTAINER") & (pallets["n_codigos"] > 1)

    return pallets


def dibujar_caja_3d(fig, x0, x1, y0, y1, z0, z1, color="red", ancho_linea=4):
    aristas = [
        ([x0, x1], [y0, y0], [z0, z0]), ([x1, x1], [y0, y1], [z0, z0]),
        ([x1, x0], [y1, y1], [z0, z0]), ([x0, x0], [y1, y0], [z0, z0]),
        ([x0, x1], [y0, y0], [z1, z1]), ([x1, x1], [y0, y1], [z1, z1]),
        ([x1, x0], [y1, y1], [z1, z1]), ([x0, x0], [y1, y0], [z1, z1]),
        ([x0, x0], [y0, y0], [z0, z1]), ([x1, x1], [y0, y0], [z0, z1]),
        ([x1, x1], [y1, y1], [z0, z1]), ([x0, x0], [y1, y1], [z0, z1]),
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
    st.title("🚛 Caja seca 3D — carga real")
    st.success("Módulo cargado correctamente")

    archivo = _obtener_archivo_entrada()
    if archivo is None:
        st.info("Esperando archivo CSV (colócalo en data/ o súbelo aquí).")
        return

    detalle = cargar_detalle(archivo)
    pallets = construir_pallets(detalle)

    # ---------------- Panel de calidad de datos ----------------
    with st.expander("📋 Calidad de datos", expanded=False):
        n_anom = int(pallets["anomalia_full"].sum())
        resumen_carga = pallets.groupby("nro_carga").size()
        st.write(f"- Pallets totales: **{len(pallets)}**  |  Cargas totales: **{pallets['nro_carga'].nunique()}**")
        st.write(f"- Pallets `FULL-CONTAINER` con más de 1 código (viola la regla Full = 1 código): **{n_anom}**")
        st.write(
            f"- Pallets por carga: mín **{resumen_carga.min()}**, mediana **{int(resumen_carga.median())}**, "
            f"máx **{resumen_carga.max()}**"
        )
        if resumen_carga.max() > 40:
            st.warning(
                "Hay cargas con muchos más pallets de los que caben en un solo contenedor. "
                "'Nro Carga' podría agrupar más de un vehículo -- a confirmar."
            )

    # ---------------- Dimensiones (editables) ----------------
    st.sidebar.header("Contenedor (m)")
    largo = st.sidebar.number_input("Largo", value=20.0, step=0.1)
    ancho = st.sidebar.number_input("Ancho", value=2.5, step=0.1)
    alto = st.sidebar.number_input("Alto", value=2.6, step=0.1)

    st.sidebar.header("Pallet (cm)")
    pallet_ancho_cm = st.sidebar.number_input("Ancho pallet", value=130.0, step=1.0)
    pallet_largo_cm = st.sidebar.number_input("Largo pallet", value=120.0, step=1.0)
    pallet_alto_base_cm = st.sidebar.number_input("Alto base pallet", value=15.0, step=1.0)
    invertir = st.sidebar.checkbox(
        "Girar 90° (calzar 2 por fila)",
        value=True,
        help="130 cm no cabe 2 veces en un contenedor de 2.5 m de ancho; girado, 120 cm sí (2x120=240).",
    )

    p_ancho, p_largo = pallet_ancho_cm / 100, pallet_largo_cm / 100
    if invertir:
        p_ancho, p_largo = p_largo, p_ancho
    p_alto_base = pallet_alto_base_cm / 100
    area_pallet = p_ancho * p_largo

    por_fila = max(int(ancho // p_ancho), 1)
    por_columna = max(int(largo // p_largo), 1)
    capacidad = por_fila * por_columna
    st.sidebar.metric("Capacidad estimada", f"{capacidad} pallets", f"{por_fila} × {por_columna} en profundidad")

    # ---------------- Selector de carga ----------------
    cargas = sorted(pallets["nro_carga"].unique())
    carga_sel = st.selectbox("Nro de Carga", cargas)

    pallets_carga = pallets[pallets["nro_carga"] == carga_sel].reset_index(drop=True)
    cantidad = len(pallets_carga)

    if cantidad > capacidad:
        st.error(
            f"⚠️ Esta carga tiene {cantidad} pallets, pero con estas dimensiones sólo caben {capacidad}. "
            "Ajusta las medidas en la barra lateral o revisa si esta carga va en más de un vehículo."
        )

    # ---------------- Figura 3D ----------------
    fig = go.Figure()
    dibujar_caja_3d(fig, 0, largo, 0, ancho, 0, alto, color="black", ancho_linea=5)

    for i, fila in pallets_carga.iterrows():
        if i >= capacidad:
            break
        columna = i // por_fila
        pos_en_fila = i % por_fila

        x0, x1 = columna * p_largo, columna * p_largo + p_largo
        y0, y1 = pos_en_fila * p_ancho, pos_en_fila * p_ancho + p_ancho

        # Altura real estimada a partir del volumen reportado (Volum / area del pallet),
        # con piso en la altura base y techo en la altura del contenedor.
        vol = fila["volumen_m3"]
        altura_est = (vol / area_pallet) if pd.notna(vol) and vol > 0 else p_alto_base
        z1 = max(p_alto_base, min(altura_est, alto))

        color = "orange" if fila["anomalia_full"] else ("crimson" if fila["tipo"] == "FULL-CONTAINER" else "royalblue")

        dibujar_caja_3d(fig, x0, x1, y0, y1, 0, z1, color=color, ancho_linea=3)
        fig.add_trace(
            go.Scatter3d(
                x=[(x0 + x1) / 2], y=[(y0 + y1) / 2], z=[z1],
                mode="text", text=[fila["lpn"][-5:]], textposition="top center", showlegend=False,
            )
        )

    fig.update_layout(
        height=800,
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

    # ---------------- Tabla y totales ----------------
    st.subheader(f"Pallets de la carga {carga_sel}")
    st.dataframe(
        pallets_carga[["lpn", "tipo", "n_codigos", "codigos", "cajas", "peso_kg", "volumen_m3", "anomalia_full"]]
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Pallets", cantidad)
    c2.metric("Peso total (kg)", f"{pallets_carga['peso_kg'].sum():,.0f}")
    c3.metric("Volumen total (m³)", f"{pallets_carga['volumen_m3'].sum():,.2f}")


if __name__ == "__main__":
    main()
