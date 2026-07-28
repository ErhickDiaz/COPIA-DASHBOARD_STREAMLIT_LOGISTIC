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
    @st.cache_data(ttl=300)
    def cargar_datos():
        ruta = os.path.join("data", "Historico_Control_Logistico.csv")

        df = pd.read_csv(
            ruta,
            sep="\t",
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
    df["CANT_ENVIADA"] = pd.to_numeric(df["CANT_ENVIADA"], errors="coerce").fillna(0)
    df["CANT_RECIBIDA"] = pd.to_numeric(df["CANT_RECIBIDA"], errors="coerce").fillna(0)
    df["DIFERENCIA"] = pd.to_numeric(df["DIFERENCIA"], errors="coerce").fillna(0)

    # -----------------------------
    # SIDEBAR - FILTROS
    # -----------------------------
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
    ].copy()

    # ordenar por fecha ascendente
    df_filtrado = df_filtrado.sort_values(
        by="FECHA_TRANSFERENCIA",
        ascending=True
    )


    # =====================================
    # KPI LOGÍSTICA INVERSA PLANTA IDEAL
    # =====================================
    
    df_planta_salida = df_filtrado[
        df_filtrado["ORIGEN"].astype(str).str.upper().str.contains("PLANTA IDEAL", na=False)
    ]
    
    df_planta_llegada = df_filtrado[
        df_filtrado["DESTINO"].astype(str).str.upper().str.contains("PLANTA IDEAL", na=False)
    ]
    
    # Bandejas enviadas desde Planta Ideal
    salida_bg = df_planta_salida["CANT_ENVIADA"].sum()
    
    # Bandejas que vienen hacia Planta Ideal
    llegada_bg = df_planta_llegada["CANT_ENVIADA"].sum()
    
    # Pendientes hacia Planta Ideal
    pendientes_planta = df_planta_llegada[
        df_planta_llegada["ESTADO"] != "Receptado"
    ]["CANT_ENVIADA"].sum()
    
    # Diferencias asociadas a Planta Ideal
    diferencias_planta = df_planta_llegada["DIFERENCIA"].abs().sum()
    
    st.subheader("🏭 Control Planta Ideal")
    
    k1, k2, k3, k4 = st.columns(4)
    
    k1.metric(
        "📦 Salidas desde Planta Ideal",
        f"{int(salida_bg):,}".replace(",", ".")
    )
    
    k2.metric(
        "🚛 Hacia Planta Ideal",
        f"{int(llegada_bg):,}".replace(",", ".")
    )
    
    k3.metric(
        "🕒 Pendiente Recepción",
        f"{int(pendientes_planta):,}".replace(",", ".")
    )
    
    k4.metric(
        "⚠️ Diferencias",
        f"{int(diferencias_planta):,}".replace(",", ".")
    )
    
    st.divider()

    
    # -----------------------------
    # VALIDAR SI HAY DATOS
    # -----------------------------
    if df_filtrado.empty:
        st.warning("⚠️ No hay datos para los filtros seleccionados.")
        return

    # -----------------------------
    # KPIs SEGÚN FILTRO
    # -----------------------------
    total_transferencias = df_filtrado["NUM_TRANSF"].nunique()
    total_registros = len(df_filtrado)

    receptados = df_filtrado[df_filtrado["ESTADO"] == "Receptado"].shape[0]
    cancelados = df_filtrado[df_filtrado["ESTADO"] == "Cancelado"].shape[0]

    diferencias = df_filtrado[df_filtrado["DIFERENCIA"] != 0].shape[0]

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

    df_diff = df_filtrado[df_filtrado["DIFERENCIA"] != 0]

    if df_diff.empty:
        st.success("✅ Sin diferencias detectadas")
    else:
        st.warning(f"Se encontraron {len(df_diff)} registros con diferencia")
        st.dataframe(df_diff.head(50), use_container_width=True)

    st.divider()

    # -----------------------------
    # SEPARAR REQUERIDOS ROBUSTO
    # -----------------------------
    df_filtrado["REQUERIDOS"] = df_filtrado["REQUERIDOS"].fillna("").astype(str)

    def separar_requeridos(valor):
        partes = valor.split("/")

        tracto = partes[0].strip() if len(partes) > 0 else ""
        rampla = partes[1].strip() if len(partes) > 1 else ""
        carga = partes[2].strip() if len(partes) > 2 else ""

        return pd.Series([tracto, rampla, carga])

    df_filtrado[["TRACTO", "RAMPLA", "CARGA"]] = df_filtrado["REQUERIDOS"].apply(
        separar_requeridos
    )

    # -----------------------------
    # TRANSFORMACIÓN PIVOT
    # -----------------------------
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
        columns="ENVASE",
        values="CANT_ENVIADA",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    # limpiar nombre del índice de columnas
    df_pivot.columns.name = None

    # ordenar nuevamente por fecha ascendente
    df_pivot = df_pivot.sort_values(
        by="FECHA_TRANSFERENCIA",
        ascending=True
    )

    # -----------------------------
    # TABLA CONSOLIDADA
    # -----------------------------
    st.subheader("📊 Tabla consolidada por envase")
    st.dataframe(df_pivot, use_container_width=True)

    st.divider()

    # -----------------------------
    # TOTALES POR ENVASE
    # -----------------------------
    columnas_envase = [
        col for col in df_pivot.columns
        if col not in columnas_base
    ]

    if len(columnas_envase) > 0:

        totales_envase = df_pivot[columnas_envase].sum().reset_index()
        totales_envase.columns = ["ENVASE", "TOTAL"]

        # quitar envases con total 0 si quieres una tabla más limpia
        totales_envase = totales_envase[totales_envase["TOTAL"] > 0]

        st.subheader("📦 Totales por tipo de envase")

        if totales_envase.empty:
            st.info("No hay totales de envases para mostrar.")
        else:
            # tabla resumen
            st.dataframe(totales_envase, use_container_width=True)

            # KPIs dinámicos
            totales_dict = dict(zip(totales_envase["ENVASE"], totales_envase["TOTAL"]))

            cols = st.columns(len(totales_dict))

            for col, (envase, total) in zip(cols, totales_dict.items()):
                col.metric(envase, f"{int(total):,}".replace(",", "."))

            # gráfico
            st.bar_chart(totales_envase.set_index("ENVASE"))

    else:
        st.info("No se detectaron columnas de envase para totalizar.")

    st.divider()

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

        st.write("Vista previa datos filtrados:")
        st.dataframe(df_filtrado.head(20), use_container_width=True)

        st.write("Vista previa tabla pivot:")
        st.dataframe(df_pivot.head(20), use_container_width=True)


if __name__ == "__main__":
    main()
