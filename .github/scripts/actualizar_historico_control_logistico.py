from pathlib import Path
from io import StringIO
import pandas as pd


# ============================================================
# RUTAS
# ============================================================

RUTA_CONTROL = Path("data/Control_Logistico.csv")
RUTA_HISTORICO = Path("data/Historico_Control_Logistico.csv")


# ============================================================
# CLAVES DE DEDUPLICACIÓN
# ============================================================

CLAVES_DEDUP = [
    "NUM_TRANSF",
    "FECHA_TRANSFERENCIA",
    "ORIGEN",
    "DESTINO",
    "ENVASE",
    "REQUERIDOS"
]


# ============================================================
# LECTOR ROBUSTO CSV / TSV
# ============================================================

def leer_csv_robusto(ruta):
    """
    Lee archivos CSV/TSV probando:
    - utf-8-sig
    - utf-8
    - cp1252
    - latin-1

    Y separadores:
    - tabulación
    - coma
    - punto y coma
    """

    ruta = Path(ruta)

    if not ruta.exists():
        print(f"ℹ️ Archivo no existe: {ruta}")
        return pd.DataFrame()

    contenido_bytes = ruta.read_bytes()

    if len(contenido_bytes) == 0:
        print(f"ℹ️ Archivo vacío: {ruta}")
        return pd.DataFrame()

    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):

        try:
            texto = contenido_bytes.decode(encoding)

        except UnicodeDecodeError:
            continue

        for sep in ("\t", ",", ";"):

            try:
                df = pd.read_csv(
                    StringIO(texto),
                    sep=sep,
                    engine="python",
                    on_bad_lines="skip"
                )

            except pd.errors.EmptyDataError:
                continue

            except pd.errors.ParserError:
                continue

            except Exception:
                continue

            if df.shape[1] > 1:
                df.columns = df.columns.str.strip().str.upper()

                print(
                    f"✅ Archivo leído: {ruta} | "
                    f"encoding={encoding} | sep={repr(sep)} | "
                    f"filas={len(df):,}"
                )

                return df

    raise ValueError(
        f"No se pudo interpretar el archivo: {ruta}"
    )


# ============================================================
# VALIDACIONES
# ============================================================

def validar_columnas(df, nombre_archivo):
    """
    Valida que existan las columnas mínimas para deduplicar.
    """

    if df.empty:
        return

    faltantes = [
        col for col in CLAVES_DEDUP
        if col not in df.columns
    ]

    if faltantes:
        raise ValueError(
            f"Faltan columnas en {nombre_archivo}: {faltantes}. "
            f"Columnas disponibles: {list(df.columns)}"
        )


def normalizar_dataframe(df):
    """
    Normaliza estructura antes de concatenar.
    """

    if df.empty:
        return df

    df = df.copy()

    df.columns = df.columns.str.strip().str.upper()

    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).str.strip()

    return df


# ============================================================
# PROCESO PRINCIPAL
# ============================================================

def main():

    print("🚀 Iniciando actualización de histórico Control Logístico")

    df_control = leer_csv_robusto(RUTA_CONTROL)
    df_historico = leer_csv_robusto(RUTA_HISTORICO)

    if df_control.empty:
        print("⚠️ Control_Logistico.csv está vacío. No se actualizará el histórico.")
        return

    df_control = normalizar_dataframe(df_control)
    df_historico = normalizar_dataframe(df_historico)

    validar_columnas(df_control, "Control_Logistico.csv")

    if not df_historico.empty:
        validar_columnas(df_historico, "Historico_Control_Logistico.csv")

    filas_control = len(df_control)
    filas_historico_antes = len(df_historico)

    print(f"📊 Filas Control_Logistico.csv: {filas_control:,}")
    print(f"📊 Filas histórico antes: {filas_historico_antes:,}")

    if df_historico.empty:
        df_final = df_control.copy()
    else:
        df_final = pd.concat(
            [
                df_historico,
                df_control
            ],
            ignore_index=True
        )

    filas_concat = len(df_final)

    df_final = (
        df_final
        .drop_duplicates(
            subset=CLAVES_DEDUP,
            keep="last"
        )
        .reset_index(drop=True)
    )

    filas_final = len(df_final)
    duplicados_eliminados = filas_concat - filas_final

    print(f"📊 Filas concatenadas: {filas_concat:,}")
    print(f"🧹 Duplicados eliminados: {duplicados_eliminados:,}")
    print(f"📊 Filas histórico después: {filas_final:,}")

    RUTA_HISTORICO.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df_final.to_csv(
        RUTA_HISTORICO,
        index=False,
        sep="\t",
        encoding="utf-8"
    )

    print(f"✅ Histórico actualizado correctamente: {RUTA_HISTORICO}")


if __name__ == "__main__":
    main()
