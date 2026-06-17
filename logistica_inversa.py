import streamlit as st
import pandas as pd
import os

def main():

    st.title("📦 Dashboard Logística Inversa")
    st.markdown("Control de Transferencias CTL")

    st.divider()

    # -----------------------------
    # CARGA DE DATOS
    # -----------------------------
    @st.cache_data
    def cargar_datos():
        ruta = os.path.join("data", "CL_16062026_1.csv")

        df = pd.read_csv(
            ruta,
            sep=",",
            encoding="latin-1",
            engine="python",
            on_bad_lines="skip"
        )

        return df

    df = cargar_datos()

    st.success("✅ Datos cargados correctamente")

    # -----------------------------
    # LIMPIEZA BÁSICA
    # -----------------------------
    df.columns = df.columns.str.strip()

    # convertir FECHA_TRANSFERENCIA a datetime
    df["FECHA_TRANSFERENCIA"] = pd.to_datetime(
        df["FECHA_TRANSFERENCIA"],
        dayfirst=True,
        errors="coerce"
    )


    # convertir columnas numéricas
    df["CANT_ENVIADA"] = pd.to_numeric(df["CANT_ENVIADA"], errors="coerce")
    df["CANT_RECIBIDA"] = pd.to_numeric(df["CANT_RECIBIDA"], errors="coerce")
    df["DIFERENCIA"] = pd.to_numeric(df["DIFERENCIA"], errors="coerce")

    # -----------------------------
    # KPIs
    # -----------------------------
    total_transferencias = df["NUM_TRANSF"].nunique()
    total_registros = len(df)

    receptados = df[df["ESTADO"] == "Receptado"].shape[0]
    cancelados = df[df["ESTADO"] == "Cancelado"].shape[0]

    diferencias = df[df["DIFERENCIA"] != 0].shape[0]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Transferencias únicas", total_transferencias)
    col2.metric("Registros totales", total_registros)
    col3.metric("Receptados", receptados)
    col4.metric("Con diferencia ⚠️", diferencias)

    st.divider()

    # -----------------------------
    # ALERTA DE DIFERENCIAS
    # -----------------------------
    st.subheader("⚠️ Transferencias con diferencia")

    df_diff = df[df["DIFERENCIA"] != 0]

    if df_diff.empty:
        st.success("✅ Sin diferencias detectadas")
    else:
        st.warning(f"Se encontraron {len(df_diff)} registros con diferencia")
        st.dataframe(df_diff.head(50))

    st.divider()

   
    st.sidebar.markdown("### 🔍 Filtros")
    
    # -----------------------------
    # ESTADO
    # -----------------------------
    lista_estados = ["Todos"] + sorted(df["ESTADO"].dropna().unique())
    
    estado_sel = st.sidebar.multiselect(
        "Estado",
        options=lista_estados,
        default=["Todos"]
    )
    
    if "Todos" in estado_sel:
        estados = df["ESTADO"].dropna().unique()
    else:
        estados = estado_sel
    
    
    # -----------------------------
    # ORIGEN
    # -----------------------------
    lista_origen = ["Todos"] + sorted(df["ORIGEN"].dropna().unique())
    
    origen_sel = st.sidebar.multiselect(
        "Origen",
        options=lista_origen,
        default=["Todos"]
    )
    
    if "Todos" in origen_sel:
        origenes = df["ORIGEN"].dropna().unique()
    else:
        origenes = origen_sel
    
    
    # -----------------------------
    # DESTINO
    # -----------------------------
    lista_destino = ["Todos"] + sorted(df["DESTINO"].dropna().unique())
    
    destino_sel = st.sidebar.multiselect(
        "Destino",
        options=lista_destino,
        default=["Todos"]
    )
    
    if "Todos" in destino_sel:
        destinos = df["DESTINO"].dropna().unique()
    else:
        destinos = destino_sel
    
    
    # -----------------------------
    # APLICAR FILTROS
    # -----------------------------
    df_filtrado = df[
        (df["ESTADO"].isin(estados)) &
        (df["ORIGEN"].isin(origenes)) &
        (df["DESTINO"].isin(destinos))
    ]

    # ordenar por fecha ascendente
    df_filtrado = df_filtrado.sort_values(by="FECHA_TRANSFERENCIA", ascending=True)

    # -----------------------------
    # SEPARAR REQUERIDOS
    # -----------------------------
    df_filtrado[["TRACTO", "RAMPLA", "CARGA"]] = df_filtrado["REQUERIDOS"].str.split(
        "/",
        expand=True
    )


    # -----------------------------
    # TRANSFORMACIÓN (PIVOT)
    # -----------------------------
    
    # agrupamos por transferencia + datos base
    columnas_base = [
        "NUM_TRANSF",
        "FECHA_TRANSFERENCIA",
        "ORIGEN",
        "DESTINO",
        "ESTADO",
        "TRACTO",
        "RAMPLA",
        "CARGA"
    ]
        
    df_pivot = df_filtrado.pivot_table(
        index=columnas_base,
        columns="ENVASE",  # 👈 tipo de envase
        values="CANT_ENVIADA",  # 👈 puedes cambiar a recibida también
        aggfunc="sum",
        fill_value=0
    ).reset_index()
    
    # limpiar nombres de columnas (muy importante)
    df_pivot.columns.name = None


    # -----------------------------
    # TABLA
    # -----------------------------
    st.subheader("📊 Datos filtrados")
    st.subheader("📊 Tabla consolidada por envase")
    st.dataframe(df_pivot)




    # -----------------------------
    # NUEVA TABLA: TOTALES POR ENVASE
    # -----------------------------
    st.subheader("📦 Totales por tipo de envase")
    
    # identificar columnas de envase desde el pivot
    columnas_base = [
        "NUM_TRANSF",
        "FECHA_TRANSFERENCIA",
        "ORIGEN",
        "DESTINO",
        "ESTADO",
        "TRACTO",
        "RAMPLA",
        "CARGA"
    ]
    
    columnas_envase = [col for col in df_pivot.columns if col not in columnas_base]
    
    # calcular totales
    totales_envase = df_pivot[columnas_envase].sum().reset_index()
    totales_envase.columns = ["ENVASE", "TOTAL"]
    
    # ordenar por mayor volumen
    totales_envase = totales_envase.sort_values(by="TOTAL", ascending=False)
    
    # mostrar tabla
    st.dataframe(totales_envase, use_container_width=True)

    
    # -----------------------------
    # AGRUPACIÓN POR DESTINO
    # -----------------------------
    st.subheader("📦 Envíos por destino")

    df_destino = (
        df_filtrado.groupby("DESTINO")["CANT_ENVIADA"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    st.bar_chart(df_destino)

    # -----------------------------
    # DEBUG
    # -----------------------------
    with st.expander("🛠 Debug"):
        st.write("Columnas detectadas:")
        st.write(df.columns)
