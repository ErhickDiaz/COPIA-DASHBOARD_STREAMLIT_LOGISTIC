from pathlib import Path
import math
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Digital Twin T1", page_icon="🚛", layout="wide")
DATA = Path("data")
ENVASES = DATA / "catalogo_envases.csv"
DESTINOS = DATA / "catalogo_destinos.csv"
PATRON = "oblpnCLIDtmp*.csv"

COL_OBLPN = ["Nro Carga", "Dest", "Nro LPN", "Codigo", "Descripción de artículo",
             "Cant. Empacada", "Peso", "Volum", "Tipo"]
FAMILIAS = ["CAJAS", "CORRUGADOS", "BANDEJAS"]
COLORES = {"CAJAS":"royalblue", "CORRUGADOS":"darkorange", "BANDEJAS":"seagreen",
           "MIXTO":"mediumpurple", "SIN CLASIFICAR":"gray"}


def arreglar_encoding(v):
    if not isinstance(v, str): return v
    try: return v.encode("latin1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError): return v


def limpiar(v):
    if isinstance(v, str):
        v = v.strip()
        if v.startswith('="'):
            v = v[2:-1] if v.endswith('"') else v[2:]
    return v


def codigo(v):
    v = limpiar(v)
    if pd.isna(v): return pd.NA
    v = str(v).strip()
    return v[:-2] if v.endswith(".0") else v


def familia(v):
    if pd.isna(v): return "SIN CLASIFICAR"
    v = arreglar_encoding(str(v)).strip().upper()
    return {"CAJA":"CAJAS", "CAJAS":"CAJAS", "CORRUGADO":"CORRUGADOS",
            "CORRUGADOS":"CORRUGADOS", "BANDEJA":"BANDEJAS",
            "BANDEJAS":"BANDEJAS"}.get(v, "SIN CLASIFICAR")


def leer_csv(origen):
    try:
        return pd.read_csv(origen, sep=";", dtype=str, encoding="utf-8-sig", low_memory=False)
    except UnicodeDecodeError:
        if hasattr(origen, "seek"): origen.seek(0)
        return pd.read_csv(origen, sep=";", dtype=str, encoding="latin1", low_memory=False)


def archivo_oblpn():
    DATA.mkdir(exist_ok=True)
    files = sorted(DATA.glob(PATRON), key=lambda p: p.stat().st_mtime, reverse=True)
    if files:
        name = st.selectbox("Archivo OBLPN", [p.name for p in files])
        return DATA / name
    return st.file_uploader("Sube el CSV OBLPN", type="csv")


def catalogo_or_upload(path, label):
    if path.exists(): return path
    return st.sidebar.file_uploader(label, type="csv", key=path.stem)


@st.cache_data(show_spinner=False)
def cargar_catalogo_envases(origen):
    if origen is None: return pd.DataFrame(columns=["Codigo", "Familia Envase"])
    d = leer_csv(origen); d.columns = [arreglar_encoding(c).strip() for c in d.columns]
    req = {"Codigo", "Familia Envase"}
    if req - set(d.columns): raise ValueError(f"Catálogo envases sin columnas: {req-set(d.columns)}")
    d = d[["Codigo", "Familia Envase"]].copy()
    d["Codigo"] = d["Codigo"].map(codigo)
    d["Familia Envase"] = d["Familia Envase"].map(familia)
    d = d.dropna(subset=["Codigo"])
    if d["Codigo"].duplicated().any():
        vals = d.loc[d["Codigo"].duplicated(False), "Codigo"].unique()[:10]
        raise ValueError("Códigos duplicados en catálogo de envases: " + ", ".join(vals))
    return d


@st.cache_data(show_spinner=False)
def cargar_catalogo_destinos(origen):
    if origen is None: return pd.DataFrame(columns=["Dest", "Destino"])
    d = leer_csv(origen); d.columns = [arreglar_encoding(c).strip() for c in d.columns]
    req = {"Dest", "Destino"}
    if req - set(d.columns): raise ValueError(f"Catálogo destinos sin columnas: {req-set(d.columns)}")
    d = d[["Dest", "Destino"]].copy()
    d["Dest"] = d["Dest"].map(codigo)
    d["Destino"] = d["Destino"].fillna("").map(arreglar_encoding).str.strip().str.upper()
    d = d.dropna(subset=["Dest"])
    if d["Dest"].duplicated().any():
        vals = d.loc[d["Dest"].duplicated(False), "Dest"].unique()[:10]
        raise ValueError("Destinos duplicados: " + ", ".join(vals))
    return d


@st.cache_data(show_spinner=False)
def cargar_detalle(origen, cat_env, cat_dest):
    d = leer_csv(origen); d.columns = [arreglar_encoding(c).strip() for c in d.columns]
    faltan = set(COL_OBLPN) - set(d.columns)
    if faltan: raise ValueError("OBLPN sin columnas: " + ", ".join(sorted(faltan)))
    d = d[COL_OBLPN].copy()
    for c in d.columns: d[c] = d[c].map(limpiar).map(arreglar_encoding)
    for c in ["Nro Carga", "Dest", "Nro LPN", "Codigo"]: d[c] = d[c].map(codigo)
    for c in ["Cant. Empacada", "Peso", "Volum"]:
        d[c] = pd.to_numeric(d[c].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    d = d.dropna(subset=["Nro Carga", "Nro LPN"])
    if cat_env.empty: d["Familia Envase"] = "SIN CLASIFICAR"
    else: d = d.merge(cat_env, how="left", on="Codigo", validate="many_to_one")
    if cat_dest.empty: d["Destino"] = pd.NA
    else: d = d.merge(cat_dest, how="left", on="Dest", validate="many_to_one")
    d["Familia Envase"] = d["Familia Envase"].fillna("SIN CLASIFICAR").map(familia)
    d["Destino catalogado"] = d["Destino"].notna() & d["Destino"].ne("")
    d["Destino"] = d["Destino"].fillna(d["Dest"])
    return d


def unir(s): return ", ".join(sorted(set(s.dropna().astype(str).str.strip()) - {""}))


def clasificar_familia(row):
    presentes = [f for f, c in [("CAJAS", row["cantidad_cajas"]),
                                 ("CORRUGADOS", row["cantidad_corrugados"]),
                                 ("BANDEJAS", row["cantidad_bandejas"])] if c > 0]
    if len(presentes) > 1: return "MIXTO"
    if len(presentes) == 1: return presentes[0]
    return "SIN CLASIFICAR"


@st.cache_data(show_spinner=False)
def construir_pallets(d):
    keys = ["Nro Carga", "Dest", "Destino", "Nro LPN"]
    p = d.groupby(keys, dropna=False).agg(
        tipo_preparacion=("Tipo", "first"), n_codigos=("Codigo", "nunique"),
        codigos=("Codigo", unir), cantidad_empacada=("Cant. Empacada", "sum"),
        peso_g=("Peso", "first"), volumen_wms=("Volum", "first"),
        familias=("Familia Envase", unir)).reset_index()
    comp = d.groupby(keys + ["Familia Envase"], dropna=False)["Cant. Empacada"].sum().unstack(fill_value=0).reset_index()
    rename = {"Nro Carga":"nro_carga", "Dest":"codigo_destino", "Destino":"destino", "Nro LPN":"lpn",
              "CAJAS":"cantidad_cajas", "CORRUGADOS":"cantidad_corrugados",
              "BANDEJAS":"cantidad_bandejas", "SIN CLASIFICAR":"cantidad_sin_clasificar"}
    p = p.rename(columns=rename); comp = comp.rename(columns=rename)
    fam_cols = ["cantidad_cajas", "cantidad_corrugados", "cantidad_bandejas", "cantidad_sin_clasificar"]
    for c in fam_cols:
        if c not in comp: comp[c] = 0.0
    join = ["nro_carga", "codigo_destino", "destino", "lpn"]
    p = p.merge(comp[join + fam_cols], on=join, how="left", validate="one_to_one")
    p[fam_cols] = p[fam_cols].fillna(0)
    p["peso_kg"] = p["peso_g"] / 1000
    p["anomalia_full"] = p["tipo_preparacion"].fillna("").str.upper().eq("FULL-CONTAINER") & p["n_codigos"].gt(1)
    p["familia_visual"] = p.apply(clasificar_familia, axis=1)
    return p


def wire(fig, x0, x1, y0, y1, z0, z1, color="black", width=3, hover=None):
    edges = [([x0,x1],[y0,y0],[z0,z0]),([x1,x1],[y0,y1],[z0,z0]),([x1,x0],[y1,y1],[z0,z0]),([x0,x0],[y1,y0],[z0,z0]),
             ([x0,x1],[y0,y0],[z1,z1]),([x1,x1],[y0,y1],[z1,z1]),([x1,x0],[y1,y1],[z1,z1]),([x0,x0],[y1,y0],[z1,z1]),
             ([x0,x0],[y0,y0],[z0,z1]),([x1,x1],[y0,y0],[z0,z1]),([x1,x1],[y1,y1],[z0,z1]),([x0,x0],[y1,y1],[z0,z1])]
    for xs,ys,zs in edges:
        fig.add_trace(go.Scatter3d(x=xs,y=ys,z=zs,mode="lines",line=dict(color=color,width=width),showlegend=False,
                                   hovertext=hover,hoverinfo="text" if hover else "skip"))


def solid(fig, x0, x1, y0, y1, z0, z1, color, hover, opacity=.9):
    fig.add_trace(go.Mesh3d(
        x=[x0,x1,x1,x0,x0,x1,x1,x0], y=[y0,y0,y1,y1,y0,y0,y1,y1], z=[z0,z0,z0,z0,z1,z1,z1,z1],
        i=[0,0,4,4,0,0,1,1,2,2,3,3], j=[1,2,5,6,1,5,2,6,3,7,0,4], k=[2,3,6,7,5,4,6,5,7,6,4,7],
        color=color, opacity=opacity, flatshading=True, showlegend=False, hovertext=hover, hoverinfo="text"))


def dibujar_pallet(fig, row, x0, x1, y0, y1, z1, hover):
    mx, my = (x1-x0)*.035, (y1-y0)*.035
    familia_vis = row["familia_visual"]
    # Un código: bloque completo, color entero de la familia.
    if row["n_codigos"] == 1:
        solid(fig,x0+mx,x1-mx,y0+my,y1-my,.02,z1,COLORES.get(familia_vis,"gray"),hover,.96)
    elif familia_vis == "MIXTO":
        grupos = [("CAJAS",row["cantidad_cajas"]),("CORRUGADOS",row["cantidad_corrugados"]),
                  ("BANDEJAS",row["cantidad_bandejas"])]
        grupos = [(f,float(q)) for f,q in grupos if q > 0]
        total = sum(q for _,q in grupos); cursor=x0+mx; util=(x1-x0)-2*mx
        for idx,(f,q) in enumerate(grupos):
            fin = x1-mx if idx == len(grupos)-1 else cursor + util*(q/total)
            solid(fig,cursor,fin,y0+my,y1-my,.02,z1,COLORES[f],hover+f"<br>{f}: {q:,.0f}",.92)
            cursor=fin
    else:
        solid(fig,x0+mx,x1-mx,y0+my,y1-my,.02,z1,COLORES.get(familia_vis,"gray"),hover,.70)
    wire(fig,x0,x1,y0,y1,0,z1,"crimson" if row["anomalia_full"] else "#202020",2,hover)


def main():
    st.title("🚛 Caja seca 3D | Carga real por LPN")
    st.caption("Se muestran todos los pallets. La remontada se incorporará en una etapa posterior.")
    oblpn = archivo_oblpn()
    if oblpn is None: st.stop()
    env = catalogo_or_upload(ENVASES,"Sube catalogo_envases.csv")
    dest = catalogo_or_upload(DESTINOS,"Sube catalogo_destinos.csv")
    try:
        det = cargar_detalle(oblpn,cargar_catalogo_envases(env),cargar_catalogo_destinos(dest))
        pallets = construir_pallets(det)
    except Exception as e:
        st.error(f"No fue posible cargar los datos: {e}"); st.stop()

    with st.expander("📋 Calidad de datos"):
        st.write(f"Pallets: **{len(pallets):,}** | Cargas: **{pallets['nro_carga'].nunique():,}**")
        st.write(f"Códigos sin familia: **{det.loc[det['Familia Envase'].eq('SIN CLASIFICAR'),'Codigo'].nunique():,}**")
        st.write(f"Destinos sin catálogo: **{det.loc[~det['Destino catalogado'],'Dest'].nunique():,}**")

    st.sidebar.header("Contenedor (m)")
    largo=st.sidebar.number_input("Largo",1.0,value=20.0,step=.1); ancho=st.sidebar.number_input("Ancho",1.0,value=2.5,step=.1)
    alto=st.sidebar.number_input("Alto",1.0,value=2.6,step=.1)
    st.sidebar.header("Pallet (cm)")
    pa=st.sidebar.number_input("Ancho pallet",1.0,value=130.0); pl=st.sidebar.number_input("Largo pallet",1.0,value=120.0)
    base=st.sidebar.number_input("Alto base",1.0,value=15.0); girar=st.sidebar.checkbox("Girar 90°",True)
    factor=st.sidebar.number_input("Factor Volum WMS a m³",.000001,value=1.0,format="%.6f")
    p_ancho,p_largo=pa/100,pl/100
    if girar: p_ancho,p_largo=p_largo,p_ancho
    por_fila=max(int(ancho//p_ancho),1); capacidad=por_fila*max(int(largo//p_largo),1)
    st.sidebar.metric("Capacidad geométrica",f"{capacidad} pallets")

    opts=pallets[["nro_carga","codigo_destino","destino"]].drop_duplicates().sort_values(["nro_carga","destino"])
    opts["label"]=opts["nro_carga"]+" | "+opts["destino"]+" ["+opts["codigo_destino"]+"]"
    label=st.selectbox("N.º de carga + destino",opts["label"])
    sel=opts.loc[opts["label"].eq(label)].iloc[0]
    pc=pallets.loc[pallets["nro_carga"].eq(sel.nro_carga)&pallets["codigo_destino"].eq(sel.codigo_destino)].sort_values("lpn").reset_index(drop=True)
    pc["volumen_m3_estimado"]=pc["volumen_wms"]*factor
    total_bultos=pc["cantidad_empacada"].sum(); n=len(pc)
    cols=max(1,math.ceil(n/por_fila)); largo_visual=max(largo,cols*p_largo)
    if n>capacidad: st.warning(f"Hay {n} pallets y la capacidad geométrica es {capacidad}. Se grafican todos sin remontada.")

    fig=go.Figure(); wire(fig,0,largo,0,ancho,0,alto,"black",5)
    area=p_ancho*p_largo
    for idx,row in pc.iterrows():
        col=idx//por_fila; pos=idx%por_fila
        x0,x1=col*p_largo,(col+1)*p_largo; y0,y1=pos*p_ancho,(pos+1)*p_ancho
        vol=row["volumen_m3_estimado"]; z1=max(base/100,min((vol/area if pd.notna(vol) and vol>0 else base/100),alto))
        h=(f"LPN: {row.lpn}<br>Familia: {row.familia_visual}<br>Códigos: {row.n_codigos}<br>"
           f"Bultos empacados: {row.cantidad_empacada:,.0f}<br>Cajas: {row.cantidad_cajas:,.0f}<br>"
           f"Corrugados: {row.cantidad_corrugados:,.0f}<br>Bandejas: {row.cantidad_bandejas:,.0f}")
        dibujar_pallet(fig,row,x0,x1,y0,y1,z1,h)
        texto=f"{str(row.lpn)[-7:]}<br>{row.familia_visual}<br>{row.cantidad_empacada:,.0f} bultos"
        fig.add_trace(go.Scatter3d(x=[(x0+x1)/2],y=[(y0+y1)/2],z=[z1],mode="text",text=[texto],showlegend=False,hovertext=h,hoverinfo="text"))
    for f in sorted(set(pc["familia_visual"])|set(FAMILIAS)):
        fig.add_trace(go.Scatter3d(x=[None],y=[None],z=[None],mode="markers",marker=dict(size=8,color=COLORES.get(f,"gray")),name=f))
    fig.update_layout(height=800,margin=dict(l=0,r=0,t=30,b=0),scene=dict(
        xaxis=dict(title="Largo / secuencia visual (m)",range=[0,largo_visual]),yaxis=dict(title="Ancho (m)",range=[0,ancho]),
        zaxis=dict(title="Alto estimado (m)",range=[0,alto]),camera=dict(eye=dict(x=1.5,y=1.5,z=.8)),aspectmode="manual",
        aspectratio=dict(x=max(largo_visual/4,3),y=1,z=1)))
    st.plotly_chart(fig,use_container_width=True,config={"displaylogo":False})

    c1,c2,c3,c4=st.columns(4); c1.metric("Pallets",f"{n:,}"); c2.metric("Bultos empacados",f"{total_bultos:,.0f}")
    c3.metric("Peso total (kg)",f"{pc['peso_kg'].sum():,.0f}"); c4.metric("Volumen estimado (m³)",f"{pc['volumen_m3_estimado'].sum():,.2f}")
    st.subheader("Detalle por LPN")
    st.dataframe(pc[["lpn","familia_visual","familias","n_codigos","codigos","cantidad_empacada","cantidad_cajas",
                     "cantidad_corrugados","cantidad_bandejas","peso_kg","volumen_wms","anomalia_full"]],use_container_width=True,hide_index=True)
    st.success(f"📦 Total de bultos empacados de la carga {sel.nro_carga} | {sel.destino}: **{total_bultos:,.0f}**")

if __name__ == "__main__": main()
