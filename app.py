import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta

# CONFIGURACIÓN
st.set_page_config(page_title="PUE Champlitte v3.1", page_icon="🍰", layout="centered")

# CSS
st.markdown("""
<style>

.stApp { background-color: #FFFFFF; }

h1, h2, h3, p, label, .stMarkdown, span {
color:#000000 !important;
}

header[data-testid="stHeader"] {
visibility:hidden;
}

input {
color:#FFFFFF !important;
background-color:#444444 !important;
border-radius:10px !important;
border:2px solid #b08d15 !important;
}

div[data-baseweb="select"] *{
font-size:14px !important;
cursor:pointer !important;
}

div.stButton > button {
width:100%;
border-radius:10px;
height:3.5em;
background-color:#fff2bd !important;
color:#000000 !important;
font-weight:bold;
border:1px solid #e0d5a6 !important;
}

.confirmacion {
background:#e8ffe8;
border:2px solid #38a169;
border-radius:12px;
padding:15px;
margin-top:10px;
font-size:18px;
font-weight:bold;
color:#206b2d;
}

</style>
""", unsafe_allow_html=True)

# BASE DATOS
DB_FILE="data_champlitte_v31.json"

def cargar_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,"r") as f:
                return json.load(f)
        except:
            pass
    return {"historial":[],"totales":{},"iniciales":{}}

def guardar_db(datos):
    with open(DB_FILE,"w") as f:
        json.dump(datos,f,indent=4)

datos=cargar_db()
hoy=datetime.now().strftime('%Y-%m-%d')

# LOGO
if os.path.exists("champlitte.jpg"):
    st.image("champlitte.jpg",width=120)
else:
    st.title("🍰 CHAMPLITTE")

# PRODUCTOS
productos={
"":0,
"BOLSA PAPEL CAFE #5":0.832,
"BOLSA PAPEL CAFE #6":0.870,
"BOLSA PAPEL CAFE #14":1.364,
"BOLSA PAPEL CAFE #20":1.616,
"CAJA TUTIS":0.048,
"CAPACILLO CHINO":0.00104,
"CAPACILLO ROJO #72":0.000436,
"CONT BISAGRA":0.014,
"CUCHARA DESECHABLE":0.00165,
"ETIQUETA 4X4":0.000328,
"ETIQUETA 6X6":0.00057,
"EMPLAYE GRANDE":1.174,
"PAPEL ALUMINIO":1.342,
"SERVILLETA PQ/500":0.001192,
"COFIA":0.238,
"GUANTES POLIURETANO":0.086,
"HIGIENICO SCOTT":0.500,
"TOALLA ROLLO 180M":1.115,
"BOLSA LOCK":0.018,
"CAJA DE GRAPAS":0.176,
"CINTA EMPAQUE":0.272,
"CINTA DELIMITADORA":0.346,
"TRASLADO VALORES":0.0086,
"ETIQUETA 13X19":0.050,
"HOJAS BLANCAS PQ/500":2.146,
"TINTA EPSON 544":0.078
}

# SESSION STATE
if "reset_select" not in st.session_state:
    st.session_state.reset_select = 0

if "peso_input" not in st.session_state:
    st.session_state.peso_input=""

if "tara_input" not in st.session_state:
    st.session_state.tara_input=""

if "tara_check" not in st.session_state:
    st.session_state.tara_check=False

# LIMPIAR
if st.button("🔄 LIMPIAR / MODO MANUAL"):

    st.session_state.reset_select += 1
    st.session_state.peso_input=""
    st.session_state.tara_input=""
    st.session_state.tara_check=False

    st.rerun()

# SELECTOR
opcion=st.selectbox(
"SELECCIONA ARTÍCULO",
sorted(productos.keys()),
key=f"p_sel_{st.session_state.reset_select}"
)

# INVENTARIO
if opcion!="":

    if hoy not in datos["iniciales"]:
        datos["iniciales"][hoy]={}

    if opcion not in datos["iniciales"][hoy]:

        ayer=(datetime.now()-timedelta(days=1)).strftime('%Y-%m-%d')

        ini_ayer=datos.get("iniciales",{}).get(ayer,{}).get(opcion,0)
        tot_ayer=datos.get("totales",{}).get(ayer,{}).get(opcion,0)

        datos["iniciales"][hoy][opcion]=max(0,ini_ayer-tot_ayer)

        guardar_db(datos)

    with st.expander("📝 Ajustar Inventario Inicial"):

        ini_txt=st.text_input("Cantidad actual",value="")

        if st.button("GUARDAR INICIAL"):

            try:
                nuevo_ini=float(ini_txt)
            except:
                nuevo_ini=0

            datos["iniciales"][hoy][opcion]=nuevo_ini
            guardar_db(datos)
            st.rerun()

# REGISTRO
st.write(f"### ⚖️ Registro: {opcion if opcion!='' else 'Modo Libre'}")

modo_libre=opcion==""

if modo_libre:
    st.info("Modo libre activado")

pue=productos.get(opcion,0)

col1,col2=st.columns(2)

with col1:

    peso_txt=st.text_input(
    "Peso Báscula",
    key="peso_input"
    )

    try:
        peso_total=float(peso_txt)
    except:
        peso_total=0

with col2:

    t_bisag=st.checkbox("Bisagra (-0.045)")
    t_cont=st.checkbox("Contenedor (-0.019)")

tara_personal=st.checkbox(
"Tara personalizada",
key="tara_check"
)

tara_extra=0

if tara_personal:

    tara_txt=st.text_input(
    "Peso tara personalizada",
    key="tara_input"
    )

    try:
        tara_extra=float(tara_txt)
    except:
        tara_extra=0

# PUE LIBRE
if modo_libre:

    pue_txt=st.text_input("PUE personalizado",value="")

    try:
        pue=float(pue_txt)
    except:
        pue=0

# REGISTRAR
if st.button("REGISTRAR PESADA"):

    if peso_total>0 and pue>0:

        tara_calc = (0.045 if t_bisag else 0) + (0.019 if t_cont else 0)

# agregar tara personalizada
tara_real = tara_extra

# excepción tinta
if "TINTA" in opcion:
    tara_real = 0.030 + tara_extra

p_neto = peso_total - tara_real















        if p_neto>0:

            cant_res=p_neto/pue
            operacion=f"({peso_total:.3f} - {tara_real:.3f}) / {pue}"
            articulo=opcion if opcion!="" else "MODO LIBRE"

            datos["historial"].append({
                "fecha":hoy,
                "hora":datetime.now().strftime("%H:%M"),
                "art":articulo,
                "cant":round(cant_res,2),
                "op":operacion
            })

            if hoy not in datos["totales"]:
                datos["totales"][hoy]={}

            datos["totales"][hoy][articulo]=datos["totales"][hoy].get(articulo,0)+cant_res

            guardar_db(datos)

            st.markdown(f"""
            <div class="confirmacion">
            ✅ PESADA REGISTRADA<br>
            Artículo: {articulo}<br>
            Resultado: {cant_res:.2f}<br>
            Operación: {operacion}
            </div>
            """,unsafe_allow_html=True)

# HISTORIAL
st.divider()
st.subheader("🧾 Historial de Pesajes")

df_hist=pd.DataFrame(datos.get("historial",[]))

if not df_hist.empty:

    df_hoy=df_hist[df_hist["fecha"]==hoy]

    if not df_hoy.empty:

        df_hoy=df_hoy[["hora","art","cant","op"]]
        df_hoy.columns=["Hora","Artículo","Cantidad","Operación"]

        st.table(df_hoy)

# RESUMEN INVENTARIO
st.divider()
st.subheader("📊 Resumen Inventario")

productos_activos=set(
list(datos.get("iniciales",{}).get(hoy,{}).keys())+
list(datos.get("totales",{}).get(hoy,{}).keys())
)

tabla=[]

for art in productos_activos:

    ini=datos.get("iniciales",{}).get(hoy,{}).get(art,0)
    consumo=datos.get("totales",{}).get(hoy,{}).get(art,0)
    saldo=ini-consumo

    tabla.append({
        "PRODUCTO":art,
        "TENÍA":round(ini,2),
        "CONSUMO HOY":round(consumo,2),
        "SALDO":round(saldo,2)
    })

if tabla:
    df=pd.DataFrame(tabla)
    st.dataframe(df,use_container_width=True,hide_index=True)
else:
    st.info("Sin movimientos hoy")

# BORRAR TODO
st.divider()
st.subheader("⚠️ Administración de datos")

st.warning("Esta acción borrará TODO el historial y reiniciará el inventario.")

confirmar=st.checkbox("Confirmo que quiero borrar todos los registros")

if st.button("🗑 BORRAR TODOS LOS REGISTROS"):

    if confirmar:

        datos={
            "historial":[],
            "totales":{},
            "iniciales":{}
        }

        guardar_db(datos)

        st.success("Todos los registros fueron eliminados")
        st.rerun()

    else:
        st.error("Debes confirmar la eliminación.")

st.caption("Champlitte v3.1")
