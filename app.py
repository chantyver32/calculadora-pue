import streamlit as st
import pandas as pd
from PIL import Image
import os
import json
from datetime import datetime, timedelta

# 1. CONFIGURACIÓN DE PÁGINA (Layout centrado es mejor para móvil)
st.set_page_config(page_title="PUE Champlitte v2.8", page_icon="🍰", layout="centered")

# 2. CSS: OPTIMIZACIÓN MÓVIL Y ESTILO V1.1
st.markdown(
    """
    <style>
    /* Evitar scroll horizontal y ajustar fondo */
    .stApp { 
        background-color: #FFFFFF; 
    }
    
    /* Ajuste de contenedor principal para móviles */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }

    /* Texto general en Negro */
    .stApp, p, label, .stMarkdown, div[data-testid="stMarkdownContainer"] p {
        color: #000000 !important;
    }

    header[data-testid="stHeader"] { visibility: hidden; }

    /* INPUTS: Optimizados para dedos */
    input {
        color: #000000 !important;
        background-color: #FFFFFF !important;
        font-size: 18px !important; /* Evita el zoom automático en iOS */
        height: 50px !important;
        border-radius: 10px !important;
        border: 1px solid #e0d5a6 !important;
    }

    /* BOTONES: Más grandes y fáciles de tocar (Touch-friendly) */
    div.stButton > button {
        width: 100% !important;
        border-radius: 12px !important;
        height: 4em !important; /* Más altos para móviles */
        background-color: #fff2bd !important;
        color: #000000 !important;
        font-weight: bold !important;
        font-size: 18px !important;
        border: 1px solid #e0d5a6 !important;
        margin-bottom: 10px !important;
        transition: transform 0.1s;
    }
    div.stButton > button:active { transform: scale(0.95); }
    
    /* MÉTRICAS: Ajustadas para que no se desborden en pantallas pequeñas */
    div[data-testid="stMetricValue"] { 
        font-size: 38px !important; 
        color: #b08d15 !important; 
        font-weight: 900 !important;
        line-height: 1.2 !important;
    }
    
    div[data-testid="stMetricLabel"] {
        font-size: 14px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Ajuste de columnas en móvil (forzar que no sean demasiado estrechas) */
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 calc(50% - 1rem) !important;
        min-width: 150px !important;
    }

    /* Ocultar decoraciones innecesarias en móvil */
    .stDivider { margin: 1rem 0 !important; }
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

def limpiar_campos():
    st.session_state["peso_input"] = None
    # No limpiamos el selector de producto para agilizar el re-ingreso

# --- LOGO ---
col_logo, _ = st.columns([1, 1])
with col_logo:
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

# --- INTERFAZ PRINCIPAL ---
opcion = st.selectbox("ARTÍCULO:", sorted(list(productos.keys())), key="p_sel")

if opcion != "":
    datos = cargar_db()
    hoy = datetime.now().strftime('%Y-%m-%d')
    
    # Manejo de Inventario Inicial
    if hoy not in datos["iniciales"]: datos["iniciales"][hoy] = {}
    val_ini = datos["iniciales"][hoy].get(opcion, 0.0)

    with st.expander("📝 AJUSTAR INICIAL"):
        nuevo_ini = st.number_input("CANTIDAD INICIAL:", value=float(val_ini))
        if st.button("GUARDAR INICIAL"):
            datos["iniciales"][hoy][opcion] = nuevo_ini
            guardar_db(datos)
            st.rerun()

    st.divider()

    # Registro de Peso
    st.write(f"**⚖️ REGISTRO:** {opcion}")
    pue = productos[opcion]
    es_tinta = "TINTA" in opcion

    # Inputs uno debajo del otro para mejor manejo en móvil
    peso_total = st.number_input("PESO TOTAL:", format="%.3f", step=0.001, value=None, placeholder="0.000", key="peso_input")
    
    if not es_tinta:
        col_t1, col_t2 = st.columns(2)
        with col_t1: t_cont = st.checkbox("Contenedor")
        with col_t2: t_bisag = st.checkbox("Bisagra")
    else:
        st.info("Descuento tinta: 0.030")

    # Botones grandes
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

    # Resultados en métricas grandes
    total_salida = datos["totales"].get(hoy, {}).get(opcion, 0.0)
    disponible = max(0.0, val_ini - total_salida)

    st.markdown("---")
    m1, m2 = st.columns(2)
    m1.metric("SALIDA HOY", f"{total_salida:,.1f}")
    m2.metric("DISPONIBLE", f"{disponible:,.1f}")

    if st.checkbox("Ver historial hoy"):
        df = pd.DataFrame([h for h in datos["historial"] if h["fecha"] == hoy and h["art"] == opcion])
        if not df.empty:
            st.dataframe(df[["hora", "cant"]].sort_values("hora", ascending=False), use_container_width=True)

st.markdown("---")
if st.button("🗑️ REINICIAR DÍA"):
    datos = cargar_db()
    hoy = datetime.now().strftime('%Y-%m-%d')
    datos["totales"][hoy] = {}
    datos["historial"] = [h for h in datos["historial"] if h["fecha"] != hoy]
    guardar_db(datos)
    st.rerun()

st.caption("v2.8 - Móvil Optimizado 🍰")
