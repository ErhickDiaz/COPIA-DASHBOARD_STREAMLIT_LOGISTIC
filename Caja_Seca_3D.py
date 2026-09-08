from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# --------------------------------------------------------------------
# CONFIGURACION GENERAL
# --------------------------------------------------------------------

st.set_page_config(
    page_title="Digital Twin T1",
    page_icon="🚛",
    layout="wide",
)

RUTA_DATA = Path("data")
PATRON_OBLPN = "oblpnCLIDtmp*.csv"
ARCHIVO_ENVASES = RUTA_DATA / "catalogo_envases.csv"
ARCHIVO_DESTINOS = RUTA_DATA / "catalogo_destinos.csv"

FAMILIAS_VALIDAS = ["CAJAS", "CORRUGADOS", "BANDEJAS"]

COLORES_FAMILIA = {
    "CAJAS": "royalblue",
    "CORRUGADOS": "darkorange",
    "BANDEJAS": "seagreen",
    "MIXTO": "mediumpurple",
    "SIN CLASIFICAR": "gray",
}

COLUMNAS_UTILES = [
    "Nro Carga",
    "Dest",
    "Nro LPN",
    "Codigo",
    "Descripción de artículo",
    "Cant. Empacada",
    "Peso",
    "Volum",
    "Tipo",
]


# --------------------------------------------------------------------
# LIMPIEZA Y NORMALIZACION
# --------------------------------------------------------------------


def _arreglar_encoding(texto):
    """Corrige textos que puedan venir con doble codificación."""
    if not isinstance(texto, str):
        return texto

    try:
        return texto.encode("latin1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return texto


def _limpiar_valor(valor):
    """Limpia valores exportados por Excel con formato =\"1234\"."""
    if isinstance(valor, str):
        valor = valor.strip()

        if valor.startswith('="'):
            valor = valor[2:]

            if valor.endswith('"'):
                valor = valor[:-1]

    return valor


def _normalizar_codigo(valor):
    """Normaliza códigos para garantizar cruces consistentes."""
    valor = _limpiar_valor(valor)

    if pd.isna(valor):
        return pd.NA

    valor = str(valor).strip()

    if valor.endswith(".0"):
        valor = valor[:-2]

    return valor


def _normalizar_familia(valor):
    if pd.isna(valor):
        return "SIN CLASIFICAR"

    familia = _arreglar_encoding(str(valor)).strip().upper()

    equivalencias = {
        "CAJA": "CAJAS",
        "CAJAS": "CAJAS",
        "CORRUGADO": "CORRUGADOS",
        "CORRUGADOS": "CORRUGADOS",
        "BANDEJA": "BANDEJAS",
        "BANDEJAS": "BANDEJAS",
    }

    return equivalencias.get(familia, "SIN CLASIFICAR")


def _leer_csv(ruta_o_archivo):
    """Lee CSV separados por punto y coma con UTF-8 y fallback latin-1."""
    try:
        return pd.read_csv(
            ruta_o_archivo,
            sep=";",
            dtype=str,
            encoding="utf-8-sig",
            low_memory=False,
        )
    except UnicodeDecodeError:
        if hasattr(ruta_o_archivo, "seek"):
            ruta_o_archivo.seek(0)

        return pd.read_csv(
            ruta_o_archivo,
            sep=";",
            dtype=str,
            encoding="latin1",
            low_memory=False,
        )


# --------------------------------------------------------------------
# SELECCION DE ARCHIVOS
# --------------------------------------------------------------------


def _obtener_archivo_entrada():
    RUTA_DATA.mkdir(exist_ok=True)

    csvs = sorted(
        RUTA_DATA.glob(PATRON_OBLPN),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if csvs:
        nombres = [archivo.name for archivo in csvs]
        nombre = st.selectbox(
            "Archivo OBLPN disponible en data/",
            nombres,
            index=0,
        )
        return RUTA_DATA / nombre

    return st.file_uploader(
        "Sube el CSV OBLPN de LPN por carga",
        type="csv",
    )


def _obtener_catalogo(ruta: Path, etiqueta: str):
    if ruta.exists():
        return ruta

    st.sidebar.warning(f"No se encontró {ruta.name} en data/.")

    return st.sidebar.file_uploader(
        etiqueta,
        type="csv",
        key=f"uploader_{ruta.stem}",
    )


# --------------------------------------------------------------------
# CARGA DE CATALOGOS
# --------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def cargar_catalogo_envases(ruta_o_archivo) -> pd.DataFrame:
    if ruta_o_archivo is None:
        return pd.DataFrame(columns=["Codigo", "Familia Envase"])

    catalogo = _leer_csv(ruta_o_archivo)
    catalogo.columns = [
        _arreglar_encoding(str(columna)).strip()
        for columna in catalogo.columns
    ]

    requeridas = {"Codigo", "Familia Envase"}
    faltantes = requeridas - set(catalogo.columns)

    if faltantes:
        raise ValueError(
            "Faltan columnas en el catálogo de envases: "
            + ", ".join(sorted(faltantes))
        )

    catalogo = catalogo[["Codigo", "Familia Envase"]].copy()
    catalogo["Codigo"] = catalogo["Codigo"].map(_normalizar_codigo)
    catalogo["Familia Envase"] = catalogo["Familia Envase"].map(
        _normalizar_familia
    )

    catalogo = catalogo.dropna(subset=["Codigo"])

    duplicados = catalogo[catalogo.duplicated("Codigo", keep=False)]
    if not duplicados.empty:
        ejemplos = ", ".join(duplicados["Codigo"].astype(str).unique()[:10])
        raise ValueError(
            "El catálogo de envases contiene códigos duplicados. "
            f"Ejemplos: {ejemplos}"
        )

    return catalogo.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def cargar_catalogo_destinos(ruta_o_archivo) -> pd.DataFrame:
    if ruta_o_archivo is None:
        return pd.DataFrame(columns=["Dest", "Destino"])

    catalogo = _leer_csv(ruta_o_archivo)
    catalogo.columns = [
        _arreglar_encoding(str(columna)).strip()
        for columna in catalogo.columns
    ]

    requeridas = {"Dest", "Destino"}
    faltantes = requeridas - set(catalogo.columns)

    if faltantes:
        raise ValueError(
            "Faltan columnas en el catálogo de destinos: "
            + ", ".join(sorted(faltantes))
        )

    catalogo = catalogo[["Dest", "Destino"]].copy()
    catalogo["Dest"] = catalogo["Dest"].map(_normalizar_codigo)
    catalogo["Destino"] = (
        catalogo["Destino"]
        .fillna("")
        .map(_arreglar_encoding)
        .astype(str)
        .str.strip()
        .str.upper()
    )

    catalogo = catalogo.dropna(subset=["Dest"])

    duplicados = catalogo[catalogo.duplicated("Dest", keep=False)]
    if not duplicados.empty:
        ejemplos = ", ".join(duplicados["Dest"].astype(str).unique()[:10])
        raise ValueError(
            "El catálogo de destinos contiene códigos duplicados. "
            f"Ejemplos: {ejemplos}"
        )

    return catalogo.reset_index(drop=True)


# --------------------------------------------------------------------
# CARGA Y ENRIQUECIMIENTO DEL OBLPN
# --------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def cargar_detalle(
    archivo,
    catalogo_envases: pd.DataFrame,
    catalogo_destinos: pd.DataFrame,
) -> pd.DataFrame:
    df = _leer_csv(archivo)
    df.columns = [
        _arreglar_encoding(str(columna)).strip()
        for columna in df.columns
    ]

    faltantes = set(COLUMNAS_UTILES) - set(df.columns)
    if faltantes:
        raise ValueError(
            "El archivo OBLPN no contiene las columnas requeridas: "
            + ", ".join(sorted(faltantes))
        )

    df = df[COLUMNAS_UTILES].copy()

    for columna in df.columns:
        df[columna] = (
            df[columna]
            .map(_limpiar_valor)
            .map(_arreglar_encoding)
        )

    df["Nro Carga"] = df["Nro Carga"].map(_normalizar_codigo)
    df["Nro LPN"] = df["Nro LPN"].map(_normalizar_codigo)
    df["Codigo"] = df["Codigo"].map(_normalizar_codigo)
    df["Dest"] = df["Dest"].map(_normalizar_codigo)

    for columna in ["Cant. Empacada", "Peso", "Volum"]:
        df[columna] = pd.to_numeric(
            df[columna].astype(str).str.replace(",", ".", regex=False),
            errors="coerce",
        )

    df = df.dropna(subset=["Nro Carga", "Nro LPN"])

    if not catalogo_envases.empty:
        df = df.merge(
            catalogo_envases,
            how="left",
            on="Codigo",
            validate="many_to_one",
        )
    else:
        df["Familia Envase"] = "SIN CLASIFICAR"

    if not catalogo_destinos.empty:
        df = df.merge(
            catalogo_destinos,
            how="left",
            on="Dest",
            validate="many_to_one",
        )
    else:
        df["Destino"] = pd.NA

    df["Familia Envase"] = (
        df["Familia Envase"]
        .fillna("SIN CLASIFICAR")
        .map(_normalizar_familia)
    )

    df["Destino catalogado"] = df["Destino"].notna() & df["Destino"].ne("")
    df["Destino"] = df["Destino"].fillna(df["Dest"])
    df.loc[df["Destino"].eq(""), "Destino"] = df.loc[
        df["Destino"].eq(""), "Dest"
    ]

    return df


# --------------------------------------------------------------------
# CONSTRUCCION DE PALLETS
# --------------------------------------------------------------------


def _unir_unicos(serie):
    valores = sorted(
        set(
            serie.dropna()
            .astype(str)
            .str.strip()
            .loc[lambda s: s.ne("")]
        )
    )
    return ", ".join(valores)


@st.cache_data(show_spinner=False)
def construir_pallets(df: pd.DataFrame) -> pd.DataFrame:
    agrupacion = ["Nro Carga", "Dest", "Destino", "Nro LPN"]

    pallets = (
        df.groupby(agrupacion, dropna=False)
        .agg(
            tipo_preparacion=("Tipo", "first"),
            n_codigos=("Codigo", "nunique"),
            codigos=("Codigo", _unir_unicos),
            cantidad_empacada=("Cant. Empacada", "sum"),
            peso_g=("Peso", "first"),
            volumen_wms=("Volum", "first"),
            familias=("Familia Envase", _unir_unicos),
        )
        .reset_index()
        .rename(
            columns={
                "Nro Carga": "nro_carga",
                "Dest": "codigo_destino",
                "Destino": "destino",
                "Nro LPN": "lpn",
            }
        )
    )

    composicion = (
        df.groupby(
            agrupacion + ["Familia Envase"],
            dropna=False,
        )["Cant. Empacada"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
        .rename(
            columns={
                "Nro Carga": "nro_carga",
                "Dest": "codigo_destino",
                "Destino": "destino",
                "Nro LPN": "lpn",
                "CAJAS": "cantidad_cajas",
                "CORRUGADOS": "cantidad_corrugados",
                "BANDEJAS": "cantidad_bandejas",
                "SIN CLASIFICAR": "cantidad_sin_clasificar",
            }
        )
    )

    columnas_familia = [
        "cantidad_cajas",
        "cantidad_corrugados",
        "cantidad_bandejas",
        "cantidad_sin_clasificar",
    ]

    for columna in columnas_familia:
        if columna not in composicion.columns:
            composicion[columna] = 0.0

    claves = [
        "nro_carga",
        "codigo_destino",
        "destino",
        "lpn",
    ]

    pallets = pallets.merge(
        composicion[claves + columnas_familia],
        how="left",
        on=claves,
        validate="one_to_one",
    )

    pallets[columnas_familia] = pallets[columnas_familia].fillna(0)
    pallets["peso_kg"] = pallets["peso_g"] / 1000

    pallets["anomalia_full"] = (
        pallets["tipo_preparacion"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
        .eq("FULL-CONTAINER")
        & pallets["n_codigos"].gt(1)
    )

    pallets["familia_dominante"] = pallets.apply(
        obtener_familia_dominante,
        axis=1,
    )

    return pallets


def obtener_familia_dominante(fila):
    cantidades = {
        "CAJAS": float(fila.get("cantidad_cajas", 0) or 0),
        "CORRUGADOS": float(fila.get("cantidad_corrugados", 0) or 0),
        "BANDEJAS": float(fila.get("cantidad_bandejas", 0) or 0),
    }

    positivas = {
        familia: cantidad
        for familia, cantidad in cantidades.items()
        if cantidad > 0
    }

    if not positivas:
        return "SIN CLASIFICAR"

    maximo = max(positivas.values())
    dominantes = [
        familia
        for familia, cantidad in positivas.items()
        if cantidad == maximo
    ]

    if len(dominantes) > 1:
        return "MIXTO"

    return dominantes[0]


# --------------------------------------------------------------------
# GRAFICA 3D
# --------------------------------------------------------------------


def dibujar_caja_3d(
    fig,
    x0,
    x1,
    y0,
    y1,
    z0,
    z1,
    color="red",
    ancho_linea=4,
    nombre=None,
    hover=None,
):
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

    for indice, (xs, ys, zs) in enumerate(aristas):
        fig.add_trace(
            go.Scatter3d(
                x=xs,
                y=ys,
                z=zs,
                mode="lines",
                line=dict(color=color, width=ancho_linea),
                name=nombre,
                legendgroup=nombre,
                showlegend=bool(nombre) and indice == 0,
                hovertext=hover,
                hoverinfo="text" if hover else "skip",
            )
        )


def agregar_leyenda_familias(fig, familias_presentes):
    for familia in familias_presentes:
        fig.add_trace(
            go.Scatter3d(
                x=[None],
                y=[None],
                z=[None],
                mode="markers",
                marker=dict(
                    size=8,
                    color=COLORES_FAMILIA.get(familia, "gray"),
                ),
                name=familia,
                showlegend=True,
            )
        )


# --------------------------------------------------------------------
# APLICACION
# --------------------------------------------------------------------


def main():
    st.title("🚛 Caja seca 3D | Carga real por LPN")
    st.caption(
        "La gráfica muestra todos los pallets/LPN registrados. "
        "La lógica de remontada se incorporará en una etapa posterior."
    )

    archivo_oblpn = _obtener_archivo_entrada()
    if archivo_oblpn is None:
        st.info("Coloca el OBLPN en data/ o súbelo para continuar.")
        st.stop()

    archivo_envases = _obtener_catalogo(
        ARCHIVO_ENVASES,
        "Sube catalogo_envases.csv",
    )
    archivo_destinos = _obtener_catalogo(
        ARCHIVO_DESTINOS,
        "Sube catalogo_destinos.csv",
    )

    try:
        catalogo_envases = cargar_catalogo_envases(archivo_envases)
        catalogo_destinos = cargar_catalogo_destinos(archivo_destinos)

        detalle = cargar_detalle(
            archivo_oblpn,
            catalogo_envases,
            catalogo_destinos,
        )
        pallets = construir_pallets(detalle)

    except Exception as error:
        st.error(f"No fue posible cargar los datos: {error}")
        st.stop()

    if pallets.empty:
        st.warning("No se encontraron pallets/LPN válidos en el archivo.")
        st.stop()

    # ---------------- Calidad de datos ----------------
    with st.expander("📋 Calidad de datos", expanded=False):
        n_anomalias = int(pallets["anomalia_full"].sum())
        resumen_carga = pallets.groupby("nro_carga").size()

        codigos_sin_catalogar = (
            detalle.loc[
                detalle["Familia Envase"].eq("SIN CLASIFICAR"),
                "Codigo",
            ]
            .dropna()
            .nunique()
        )

        destinos_sin_catalogar = (
            detalle.loc[
                ~detalle["Destino catalogado"],
                "Dest",
            ]
            .dropna()
            .nunique()
        )

        st.write(
            f"- Pallets totales: **{len(pallets):,}** | "
            f"Cargas totales: **{pallets['nro_carga'].nunique():,}**"
        )
        st.write(
            "- Pallets `FULL-CONTAINER` con más de un código: "
            f"**{n_anomalias:,}**"
        )
        st.write(
            f"- Pallets por carga: mín. **{resumen_carga.min():,}**, "
            f"mediana **{int(resumen_carga.median()):,}**, "
            f"máx. **{resumen_carga.max():,}**"
        )
        st.write(
            f"- Códigos sin familia de envase: "
            f"**{codigos_sin_catalogar:,}**"
        )
        st.write(
            f"- Destinos sin descripción en catálogo: "
            f"**{destinos_sin_catalogar:,}**"
        )

        if codigos_sin_catalogar:
            faltantes = (
                detalle.loc[
                    detalle["Familia Envase"].eq("SIN CLASIFICAR"),
                    ["Codigo", "Descripción de artículo"],
                ]
                .drop_duplicates()
                .sort_values("Codigo")
            )
            st.markdown("**Códigos pendientes de catalogar**")
            st.dataframe(
                faltantes,
                use_container_width=True,
                hide_index=True,
            )

    # ---------------- Dimensiones ----------------
    st.sidebar.header("Contenedor (m)")
    largo = st.sidebar.number_input(
        "Largo",
        min_value=1.0,
        value=20.0,
        step=0.1,
    )
    ancho = st.sidebar.number_input(
        "Ancho",
        min_value=1.0,
        value=2.5,
        step=0.1,
    )
    alto = st.sidebar.number_input(
        "Alto",
        min_value=1.0,
        value=2.6,
        step=0.1,
    )

    st.sidebar.header("Pallet (cm)")
    pallet_ancho_cm = st.sidebar.number_input(
        "Ancho pallet",
        min_value=1.0,
        value=130.0,
        step=1.0,
    )
    pallet_largo_cm = st.sidebar.number_input(
        "Largo pallet",
        min_value=1.0,
        value=120.0,
        step=1.0,
    )
    pallet_alto_base_cm = st.sidebar.number_input(
        "Alto base pallet",
        min_value=1.0,
        value=15.0,
        step=1.0,
    )
    holgura_cm = st.sidebar.number_input(
        "Holgura entre pallets",
        min_value=0.0,
        value=0.0,
        step=0.5,
    )

    invertir = st.sidebar.checkbox(
        "Girar 90° para calzar 2 por fila",
        value=True,
        help=(
            "Con 130 cm de ancho no caben dos pallets en 2,5 m. "
            "Girado, 120 cm permite 2 pallets por fila."
        ),
    )

    factor_volumen = st.sidebar.number_input(
        "Factor Volum WMS a m³",
        min_value=0.000001,
        value=1.0,
        format="%.6f",
        help=(
            "Se aplica como volumen_m3_estimado = Volum WMS × factor. "
            "Mantén 1,0 únicamente si Volum ya viene expresado en m³."
        ),
    )

    p_ancho = pallet_ancho_cm / 100
    p_largo = pallet_largo_cm / 100
    p_alto_base = pallet_alto_base_cm / 100
    holgura = holgura_cm / 100

    if invertir:
        p_ancho, p_largo = p_largo, p_ancho

    area_pallet = p_ancho * p_largo
    por_fila = max(int(ancho // (p_ancho + holgura)), 1)
    por_columna = max(int(largo // (p_largo + holgura)), 1)
    capacidad = por_fila * por_columna

    st.sidebar.metric(
        "Capacidad geométrica",
        f"{capacidad} pallets",
        f"{por_fila} × {por_columna}",
    )

    # ---------------- Selector carga + destino ----------------
    opciones = (
        pallets[
            [
                "nro_carga",
                "codigo_destino",
                "destino",
            ]
        ]
        .drop_duplicates()
        .sort_values(["nro_carga", "destino"])
        .reset_index(drop=True)
    )

    opciones["etiqueta"] = (
        opciones["nro_carga"].astype(str)
        + " | "
        + opciones["destino"].astype(str)
        + " ["
        + opciones["codigo_destino"].astype(str)
        + "]"
    )

    etiqueta_seleccionada = st.selectbox(
        "N.º de carga + destino",
        opciones["etiqueta"].tolist(),
    )

    seleccion = opciones.loc[
        opciones["etiqueta"].eq(etiqueta_seleccionada)
    ].iloc[0]

    carga_sel = seleccion["nro_carga"]
    codigo_destino_sel = seleccion["codigo_destino"]
    destino_sel = seleccion["destino"]

    pallets_carga = pallets.loc[
        pallets["nro_carga"].eq(carga_sel)
        & pallets["codigo_destino"].eq(codigo_destino_sel)
    ].copy()

    pallets_carga = pallets_carga.sort_values("lpn").reset_index(drop=True)
    pallets_carga["volumen_m3_estimado"] = (
        pallets_carga["volumen_wms"] * factor_volumen
    )

    cantidad = len(pallets_carga)
    columnas_necesarias = max(
        1,
        (cantidad + por_fila - 1) // por_fila,
    )
    largo_visual = max(
        largo,
        columnas_necesarias * (p_largo + holgura),
    )

    if cantidad > capacidad:
        st.warning(
            f"La selección contiene {cantidad} pallets y la capacidad "
            f"geométrica configurada es {capacidad}. Se mostrarán todos. "
            "Los pallets posteriores a la capacidad física aparecerán "
            "en una extensión visual. La remontada aún no está aplicada."
        )

    st.subheader(f"Carga {carga_sel} | {destino_sel}")

    # ---------------- Figura 3D ----------------
    fig = go.Figure()

    dibujar_caja_3d(
        fig,
        0,
        largo,
        0,
        ancho,
        0,
        alto,
        color="black",
        ancho_linea=5,
    )

    if largo_visual > largo:
        dibujar_caja_3d(
            fig,
            largo,
            largo_visual,
            0,
            ancho,
            0,
            alto,
            color="gray",
            ancho_linea=2,
        )

    familias_presentes = set()

    for indice, fila in pallets_carga.iterrows():
        columna = indice // por_fila
        posicion_fila = indice % por_fila

        x0 = columna * (p_largo + holgura)
        x1 = x0 + p_largo
        y0 = posicion_fila * (p_ancho + holgura)
        y1 = y0 + p_ancho

        volumen = fila["volumen_m3_estimado"]

        if pd.notna(volumen) and volumen > 0 and area_pallet > 0:
            altura_estimada = volumen / area_pallet
        else:
            altura_estimada = p_alto_base

        z1 = max(p_alto_base, min(altura_estimada, alto))

        familia = fila["familia_dominante"]
        familias_presentes.add(familia)
        color = COLORES_FAMILIA.get(familia, "gray")

        if fila["anomalia_full"]:
            color = "crimson"

        hover = (
            f"LPN: {fila['lpn']}<br>"
            f"Familia dominante: {familia}<br>"
            f"Tipo preparación: {fila['tipo_preparacion']}<br>"
            f"Códigos: {fila['n_codigos']}<br>"
            f"Cantidad empacada: {fila['cantidad_empacada']:,.0f}<br>"
            f"Peso: {fila['peso_kg']:,.1f} kg<br>"
            f"Volum WMS: {fila['volumen_wms']}"
        )

        dibujar_caja_3d(
            fig,
            x0,
            x1,
            y0,
            y1,
            0,
            z1,
            color=color,
            ancho_linea=4,
            hover=hover,
        )

        texto = f"{str(fila['lpn'])[-5:]}<br>{familia[:4]}"

        fig.add_trace(
            go.Scatter3d(
                x=[(x0 + x1) / 2],
                y=[(y0 + y1) / 2],
                z=[z1],
                mode="text",
                text=[texto],
                textposition="top center",
                showlegend=False,
                hovertext=hover,
                hoverinfo="text",
            )
        )

    agregar_leyenda_familias(
        fig,
        sorted(familias_presentes),
    )

    fig.update_layout(
        height=800,
        margin=dict(l=0, r=0, t=20, b=0),
        legend=dict(
            title="Familia dominante",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        scene=dict(
            xaxis=dict(
                title="Largo / secuencia visual (m)",
                range=[0, largo_visual],
            ),
            yaxis=dict(
                title="Ancho (m)",
                range=[0, ancho],
            ),
            zaxis=dict(
                title="Alto estimado (m)",
                range=[0, alto],
            ),
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=0.8)
            ),
            aspectmode="manual",
            aspectratio=dict(
                x=max(largo_visual / 4, 3),
                y=1,
                z=1,
            ),
        ),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displaylogo": False},
    )

    st.caption(
        "La posición de los pallets se simula según el orden de los LPN. "
        "Todavía no representa la secuencia física real ni la remontada."
    )

    # ---------------- Métricas ----------------
    m1, m2, m3, m4, m5, m6 = st.columns(6)

    m1.metric("Pallets", f"{cantidad:,}")
    m2.metric(
        "Peso total (kg)",
        f"{pallets_carga['peso_kg'].sum():,.0f}",
    )
    m3.metric(
        "Volumen estimado (m³)",
        f"{pallets_carga['volumen_m3_estimado'].sum():,.2f}",
    )
    m4.metric(
        "Cajas",
        f"{pallets_carga['cantidad_cajas'].sum():,.0f}",
    )
    m5.metric(
        "Corrugados",
        f"{pallets_carga['cantidad_corrugados'].sum():,.0f}",
    )
    m6.metric(
        "Bandejas",
        f"{pallets_carga['cantidad_bandejas'].sum():,.0f}",
    )

    # ---------------- Tabla de pallets ----------------
    st.subheader("Detalle por pallet/LPN")

    columnas_tabla = [
        "lpn",
        "tipo_preparacion",
        "familia_dominante",
        "familias",
        "cantidad_cajas",
        "cantidad_corrugados",
        "cantidad_bandejas",
        "cantidad_sin_clasificar",
        "n_codigos",
        "codigos",
        "cantidad_empacada",
        "peso_kg",
        "volumen_wms",
        "volumen_m3_estimado",
        "anomalia_full",
    ]

    st.dataframe(
        pallets_carga[columnas_tabla],
        use_container_width=True,
        hide_index=True,
        column_config={
            "lpn": "Nro LPN",
            "tipo_preparacion": "Tipo preparación",
            "familia_dominante": "Familia dominante",
            "familias": "Familias presentes",
            "cantidad_cajas": st.column_config.NumberColumn(
                "Cajas",
                format="%.0f",
            ),
            "cantidad_corrugados": st.column_config.NumberColumn(
                "Corrugados",
                format="%.0f",
            ),
            "cantidad_bandejas": st.column_config.NumberColumn(
                "Bandejas",
                format="%.0f",
            ),
            "cantidad_sin_clasificar": st.column_config.NumberColumn(
                "Sin clasificar",
                format="%.0f",
            ),
            "n_codigos": "N.º códigos",
            "codigos": "Códigos",
            "cantidad_empacada": st.column_config.NumberColumn(
                "Cantidad empacada",
                format="%.0f",
            ),
            "peso_kg": st.column_config.NumberColumn(
                "Peso (kg)",
                format="%.1f",
            ),
            "volumen_wms": st.column_config.NumberColumn(
                "Volum WMS",
                format="%.4f",
            ),
            "volumen_m3_estimado": st.column_config.NumberColumn(
                "Volumen estimado (m³)",
                format="%.4f",
            ),
            "anomalia_full": "Anomalía Full",
        },
    )

    # ---------------- Composición por familia ----------------
    st.subheader("Composición de la selección por familia")

    resumen_familias = pd.DataFrame(
        {
            "Familia": [
                "CAJAS",
                "CORRUGADOS",
                "BANDEJAS",
                "SIN CLASIFICAR",
            ],
            "Cantidad empacada": [
                pallets_carga["cantidad_cajas"].sum(),
                pallets_carga["cantidad_corrugados"].sum(),
                pallets_carga["cantidad_bandejas"].sum(),
                pallets_carga["cantidad_sin_clasificar"].sum(),
            ],
        }
    )

    st.dataframe(
        resumen_familias,
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()
