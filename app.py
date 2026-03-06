import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta

# ---------------------- CONFIGURACIÓN ----------------------
st.set_page_config(page_title="PUE Champlitte v3.1", page_icon="🍰", layout="centered")

# ---------------------- CSS ----------------------



# ---------------------- CSS MINIMALISTA ----------------------
st.markdown("""
<style>
/* Fondo general */
.stApp {
    background-color: #FAFAFA;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Texto general */
h1, h2, h3, h4, p, label, .stMarkdown, span {
    color: #1A1A1A !important;
}

/* Inputs, selectbox y textareas */
input, textarea, .stTextInput>div>input, .stTextArea>div>textarea, .stSelectbox>div>div>div>div>select {
    background-color: #FFFFFF !important;
    color: #1A1A1A !important;
    border: 1px solid #DDDDDD !important;
    border-radius: 6px !important;
    padding: 6px 10px !important;
}

/* Botones */
.stButton>button {
    background-color: #F5F5F5 !important;
    color: #1A1A1A !important;
    border: 1px solid #DDDDDD !important;
    border-radius: 8px !important;
    padding: 6px 16px !important;
    font-weight: 500;
    transition: background 0.2s ease;
}
.stButton>button:hover {
    background-color: #E0E0E0 !important;
}

/* Expander */
.stExpanderHeader {
    background-color: #FFFFFF !important;
    border: 1px solid #DDDDDD !important;
    border-radius: 6px !important;
    padding: 8px 12px !important;
    color: #1A1A1A !important;
}

/* Tablas */
.stDataFrame div.row_widget {
    border-bottom: 1px solid #EEE !important;
}

/* Div confirmación */
.confirmacion {
    background-color: #E6FFED;
    border-left: 4px solid #34C759;
    padding: 10px 14px;
    border-radius: 6px;
    margin: 8px 0;
    font-weight: 500;
}

/* Separadores */
.stDivider {
    border-top: 1px solid #DDD !important;
}

/* Advertencias y alertas */
.stWarning {
    background-color: #FFF4E5 !important;
    border-left: 4px solid #FFA500 !important;
}
.stError {
    background-color: #FFE5E5 !important;
    border-left: 4px solid #FF3B30 !important;
}
.stInfo {
    background-color: #E5F0FF !important;
    border-left: 4px solid #007AFF !important;
}

/* Header de Streamlit oculto */
header[data-testid="stHeader"] {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)

# ---------------------- BASE DE DATOS ----------------------
DB_FILE = "data_champlitte_v31.json"

def cargar_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"historial": [], "totales": {}, "iniciales": {}}

def guardar_db(datos):
    with open(DB_FILE, "w") as f:
        json.dump(datos, f, indent=4)

datos = cargar_db()
hoy = datetime.now().strftime('%Y-%m-%d')

# ---------------------- LOGO ----------------------
if os.path.exists("champlitte.jpg"):
    st.image("champlitte.jpg", width=120)
else:
    st.title("🍰 CHAMPLITTE")

# ---------------------- PRODUCTOS ----------------------
productos = {
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

# ---------------------- SESSION STATE ----------------------
if "reset_select" not in st.session_state: st.session_state.reset_select = 0
if "peso_input" not in st.session_state: st.session_state.peso_input = ""
if "tara_input" not in st.session_state: st.session_state.tara_input = ""
if "pue_input" not in st.session_state: st.session_state.pue_input = ""
if "ini_input" not in st.session_state: st.session_state.ini_input = ""

# ---------------------- LIMPIAR ----------------------
if st.button("🔄 LIMPIAR / MODO MANUAL"):
    st.session_state.reset_select += 1
    st.session_state.peso_input = ""
    st.session_state.tara_input = ""
    st.session_state.pue_input = ""
    st.session_state.ini_input = ""
    
# ---------------------- SELECTOR ----------------------
opcion = st.selectbox(
    "SELECCIONA ARTÍCULO", sorted(productos.keys()), 
    key=f"p_sel_{st.session_state.reset_select}"
)
articulo_actual = opcion if opcion != "" else "MODO LIBRE"

# ---------------------- INVENTARIO INICIAL ----------------------
if hoy not in datos["iniciales"]:
    datos["iniciales"][hoy] = {}
if articulo_actual not in datos["iniciales"][hoy]:
    ayer = (datetime.now()-timedelta(days=1)).strftime('%Y-%m-%d')
    ini_ayer = datos.get("iniciales",{}).get(ayer,{}).get(articulo_actual,0)
    tot_ayer = datos.get("totales",{}).get(ayer,{}).get(articulo_actual,0)
    datos["iniciales"][hoy][articulo_actual] = max(0, ini_ayer - tot_ayer)
    guardar_db(datos)

with st.expander("📝 Ajustar Inventario Inicial"):
    ini_txt = st.text_input("Cantidad actual", key="ini_input")
    if st.button("GUARDAR INICIAL"):
        try: nuevo_ini = float(ini_txt)
        except: nuevo_ini = 0
        datos["iniciales"][hoy][articulo_actual] = nuevo_ini
        guardar_db(datos)


# ---------------------- REGISTRO DE PESADA ----------------------
st.write(f"### ⚖️ Registro: {opcion if opcion!='' else 'Modo Libre'}")
modo_libre = opcion == ""
if modo_libre: st.info("Modo libre activado")
pue = productos.get(opcion,0)

col1, col2 = st.columns(2)
with col1:
    peso_txt = st.text_input("Peso Báscula", key="peso_input")
    try: peso_total = float(peso_txt)
    except: peso_total = 0
with col2:
    tipo_tara = st.radio("Tipo de tara", ["Sin tara","Bisagra","Contenedor","Personalizada"])
    tara_real = 0
    if tipo_tara == "Bisagra": tara_real = 0.045
    elif tipo_tara == "Contenedor": tara_real = 0.019
    elif tipo_tara == "Personalizada":
        tara_txt = st.text_input("Peso tara personalizada", key="tara_input")
        try: tara_real = float(tara_txt)
        except: tara_real = 0

if modo_libre:
    pue_txt = st.text_input("PUE personalizado", key="pue_input")
    try: pue = float(pue_txt)
    except: pue = 0

if st.button("REGISTRAR PESADA"):
    if peso_total > 0 and pue > 0:
        if "TINTA" in opcion: tara_real = 0.030
        p_neto = peso_total - tara_real
        if p_neto > 0:
            cant_res = p_neto / pue
            operacion = f"({peso_total:.3f} - {tara_real:.3f}) / {pue}"
            articulo = opcion if opcion!="" else "MODO LIBRE"
            datos["historial"].append({
                "fecha":hoy,
                "hora":datetime.now().strftime("%H:%M"),
                "art":articulo,
                "cant":round(cant_res,2),
                "op":operacion
            })
            if hoy not in datos["totales"]:
                datos["totales"][hoy] = {}
            datos["totales"][hoy][articulo] = datos["totales"][hoy].get(articulo,0) + cant_res
            guardar_db(datos)
            st.markdown(f"""
            <div class="confirmacion">
                ✅ PESADA REGISTRADA<br>
                Artículo: {articulo}<br>
                Resultado: {cant_res:.2f}<br>
                Operación: {operacion}
            </div>
            """, unsafe_allow_html=True)

# ---------------------- HISTORIAL ----------------------
st.divider()
st.subheader("🧾 Historial de Pesajes")
df_hist = pd.DataFrame(datos.get("historial",[]))
if not df_hist.empty:
    df_hoy = df_hist[df_hist["fecha"] == hoy]
    if not df_hoy.empty:
        df_hoy = df_hoy.reindex(columns=["hora","art","cant","op"])
        df_hoy.columns = ["Hora","Artículo","Cantidad","Operación"]
        st.table(df_hoy)

# ---------------------- RESUMEN INVENTARIO ----------------------
st.divider()
st.subheader("📊 Resumen Inventario")
productos_activos = set(list(datos.get("iniciales",{}).get(hoy,{}).keys()) + list(datos.get("totales",{}).get(hoy,{}).keys()))
tabla = []
for art in productos_activos:
    ini = datos.get("iniciales",{}).get(hoy,{}).get(art,0)
    consumo = datos.get("totales",{}).get(hoy,{}).get(art,0)
    saldo = ini - consumo
    tabla.append({"PRODUCTO":art,"TENÍA":round(ini,2),"CONSUMO HOY":round(consumo,2),"SALDO":round(saldo,2)})
if tabla:
    df = pd.DataFrame(tabla)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("Sin movimientos hoy")

# ---------------------- BORRAR TODO ----------------------
st.divider()
st.subheader("⚠️ Administración de datos")
st.warning("Esta acción borrará TODO el historial y reiniciará el inventario.")
confirmar = st.checkbox("Confirmo que quiero borrar todos los registros")

if st.button("🗑 BORRAR TODOS LOS REGISTROS"):
    if confirmar:
        datos = {"historial":[],"totales":{},"iniciales":{}}
        guardar_db(datos)
        st.success("Todos los registros fueron eliminados")
        
    else:
        st.error("Debes confirmar la eliminación.")

st.caption("Champlitte v3.1")
