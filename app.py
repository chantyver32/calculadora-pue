import streamlit as st
import pandas as pd
from PIL import Image
import os
import json
from datetime import datetime, timedelta

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="PUE Champlitte v2.8", page_icon="🍰", layout="centered")

# 2. CSS: OPTIMIZACIÓN MÓVIL Y ESTILO LIMPIO
st.markdown(
    """
    <style>
    .stApp { background-color: #FFFFFF; }
    
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }

    .stApp, p, label, .stMarkdown, div[data-testid="stMarkdownContainer"] p {
        color: #000000 !important;
    }

    header[data-testid="stHeader"] { visibility: hidden; }

    /* INPUTS: Listos para escribir */
    input {
        color: #000000 !important;
        background-color: #FFFFFF !important;
        font-size: 20px !important; 
        height: 55px !important;
        border-radius: 10px !important;
        border: 2px solid #e0d5a6 !important;
    }

    /* BOTONES GRANDES TOUCH */
    div.stButton > button {
        width: 100% !important;
        border-radius: 12px !important;
        height: 4em !important;
        background-color: #fff2bd !important;
        color: #000000 !important;
        font-weight: bold !important;
        font-size: 18px !important;
        border: 1px solid #e0d5a6 !important;
        margin-bottom: 10px !important;
    }
    div.stButton > button:active { transform: scale(0.95); }
    
    /* MÉTRICAS */
    div[data-testid="stMetricValue"] { 
        font-size: 40px !important; 
        color: #b08d15 !important; 
        font-weight: 900 !important;
    }
    </style>
    """, 
    unsafe_allow_html=True
)

# --- BASE DE DATOS ---
DB_FILE = "data_champlitte_v28.json"

def cargar_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {"historial": [], "totales": {}, "iniciales": {}}
    return {"historial": [], "totales": {}, "iniciales": {}}

def guardar_db(datos):
    with open(DB_FILE, "w") as f: json.dump(datos, f)

# --- LOGO ---
try:
    st.image(Image.open("champlitte.jpg"), width=100)
except:
    st.write("### 🍰 CHAMPLITTE")

# 3. PRODUCTOS
productos = {
    "": 0,
    "BOLSA PAPEL CAFE #5": 0.832, "BOLSA PAPEL CAFE #6": 0.870,
    "BOLSA PAPEL CAFE #14": 1.364, "BOLSA PAPEL CAFE #20": 1.616,
    "CAJA TUTIS": 0.048, "CAPACILLO CHINO": 0.00104,
    "CAPACILLO ROJO #72": 0.000436, "CONT BISAGRA": 0.014,
    "CUCHARA DESECHABLE": 0.00165, "ETIQUETA 4X4": 0.000328,
    "ETIQUETA 6X6": 0.00057, "EMPLAYE GRANDE": 1.174,
    "PAPEL ALUMINIO": 1.342, "SERVILLETA PQ/500": 0.001192,
    "COFIA": 0.238, "GUANTES POLIURETANO": 0.086,
    "HIGIENICO SCOTT": 0.500, "TOALLA ROLLO 180M": 1.115,
    "BOLSA LOCK": 0.018, "CAJA DE GRAPAS": 0.176,
    "CINTA EMPAQUE": 0.272, "CINTA DELIMITADORA": 0.346,
    "TRASLADO VALORES": 0.0086, "ETIQUETA 13X19": 0.050,
    "HOJAS BLANCAS PQ/500": 2.146, "TINTA EPSON 544": 0.078
}

# --- INTERFAZ ---
opcion = st.selectbox("ARTÍCULO:", sorted(list(productos.keys())), key="p_sel")

if opcion != "":
    datos = cargar_db()
    hoy = datetime.now().strftime('%Y-%m-%d')
    
    # Inventario Inicial
    if hoy not in datos["iniciales"]: datos["iniciales"][hoy] = {}
    val_ini = datos["iniciales"][hoy].get(opcion, 0.0)

    with st.expander("📝 CONFIGURAR INICIAL"):
        # value=None hace que el campo esté listo para recibir texto nuevo directamente
        nuevo_ini = st.number_input(f"Inicial actual: {val_ini}", value=None, placeholder="Escribe cantidad inicial...", key="input_ini")
        if st.button("ACTUALIZAR INICIAL"):
            if nuevo_ini is not None:
                datos["iniciales"][hoy][opcion] = nuevo_ini
                guardar_db(datos)
                st.rerun()

    st.divider()

    # Registro de Peso
    st.write(f"**⚖️ REGISTRO:** {opcion}")
    pue = productos[opcion]
    es_tinta = "TINTA" in opcion

    # value=None permite que no tengas que borrar el 0.000
    peso_total = st.number_input("PESO BÁSCULA:", format="%.3f", step=0.001, value=None, placeholder="0.000", key="peso_input")
    
    if not es_tinta:
        col_t1, col_t2 = st.columns(2)
        with col_t1: t_cont = st.checkbox("Contenedor")
        with col_t2: t_bisag = st.checkbox("Bisagra")
    else:
        st.info("Descuento tinta: 0.030")

    if st.button("CALCULAR Y REGISTRAR"):
        if peso_total is not None:
            tara = (0.045 if not es_tinta and t_cont else 0) + (0.016 if not es_tinta and t_bisag else 0)
            peso_neto = peso_total - (0.030 if es_tinta else tara)
            divisor = 0.078 if es_tinta else pue
            
            if peso_neto >= 0 and divisor > 0:
                cant_res = peso_neto / divisor
                datos["historial"].append({
                    "fecha": hoy, "hora": datetime.now().strftime('%H:%M'), 
                    "art": opcion, "cant": round(cant_res, 2)
                })
                if hoy not in datos["totales"]: datos["totales"][hoy] = {}
                datos["totales"][hoy][opcion] = datos["totales"][hoy].get(opcion, 0.0) + cant_res
                guardar_db(datos)
                st.rerun()

    # Resultados
    total_salida = datos["totales"].get(hoy, {}).get(opcion, 0.0)
    disponible = max(0.0, val_ini - total_salida)

    st.markdown("---")
    m1, m2 = st.columns(2)
    m1.metric("SALIDA HOY", f"{total_salida:,.1f}")
    m2.metric("DISPONIBLE", f"{disponible:,.1f}")

st.markdown("---")
if st.button("🗑️ REINICIAR DÍA"):
    datos = cargar_db()
    hoy = datetime.now().strftime('%Y-%m-%d')
    datos["totales"][hoy] = {}
    datos["historial"] = [h for h in datos["historial"] if h["fecha"] != hoy]
    guardar_db(datos)
    st.rerun()

st.caption("v2.8 - Sin necesidad de borrar ceros 🍰")
