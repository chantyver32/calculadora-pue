import streamlit as st
import pandas as pd
from PIL import Image
import os
import json
from datetime import datetime, timedelta

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="PUE Champlitte v2.8", page_icon="🍰", layout="centered")

# 2. CSS MEJORADO (Basado en tu diseño original)
st.markdown(
    """
    <style>
    .stApp { background-color: #FFFFFF; }
    
    h1, h2, h3, p, label, .stMarkdown, span {
        color: #000000 !important;
    }

    header[data-testid="stHeader"] { visibility: hidden; }

    input {
        color: #FFFFFF !important; 
        background-color: #444444 !important;
        font-size: 20px !important;
        font-weight: bold !important;
        border-radius: 10px !important;
        border: 2px solid #b08d15 !important;
    }
    
    input::placeholder { color: #BBBBBB !important; }

    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        height: 3.5em;
        background-color: #fff2bd !important;
        color: #000000 !important;
        font-weight: bold;
        border: 1px solid #e0d5a6 !important;
        transition: 0.3s;
    }
    
    div.stButton > button:hover {
        background-color: #fce895 !important;
        border: 1px solid #b08d15 !important;
    }
    
    .resumen-caja {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        border: 2px solid #f0e6bc;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.05);
        margin: 20px 0px;
    }
    
    .metric-value { font-size: 22px; font-weight: bold; color: #000; }
    .metric-total { font-size: 26px; font-weight: 900; color: #b08d15; }
    </style>
    """, 
    unsafe_allow_html=True
)

# --- LÓGICA DE BASE DE DATOS ---
DB_FILE = "data_champlitte_v27.json"

def cargar_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: 
                return json.load(f)
        except: 
            return {"historial": [], "totales": {}, "iniciales": {}}
    return {"historial": [], "totales": {}, "iniciales": {}}

def guardar_db(datos):
    with open(DB_FILE, "w") as f: 
        json.dump(datos, f, indent=4)

# --- FUNCIONES DE LIMPIEZA ---
def limpiar_campos():
    st.session_state.peso_input = 0.0
    st.session_state.t_cont = False
    st.session_state.t_bisag = False

# --- LOGO ---
if os.path.exists("champlitte.jpg"):
    st.image("champlitte.jpg", width=120)
else:
    st.title("🍰 PASTELERÍA CHAMPLITTE")

# 3. DICCIONARIO DE PRODUCTOS (PUE)
productos = {
    "": 0, "BOLSA PAPEL CAFE #5": 0.832, "BOLSA PAPEL CAFE #6": 0.870,
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

opcion = st.selectbox("SELECCIONA ARTÍCULO:", sorted(list(productos.keys())), key="p_sel")

if opcion != "":
    datos = cargar_db()
    hoy = datetime.now().strftime('%Y-%m-%d')
    ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    # --- INVENTARIO INICIAL ---
    if hoy not in datos["iniciales"]: 
        datos["iniciales"][hoy] = {}
        
    if opcion not in datos["iniciales"][hoy]:
        ini_ayer = datos.get("iniciales", {}).get(ayer, {}).get(opcion, 0.0)
        tot_ayer = datos.get("totales", {}).get(ayer, {}).get(opcion, 0.0)
        datos["iniciales"][hoy][opcion] = max(0.0, ini_ayer - tot_ayer)
        guardar_db(datos)

    val_ini = datos["iniciales"][hoy][opcion]
    
    with st.expander("📝 Configurar Inventario Inicial"):
        nuevo_ini = st.number_input("Cantidad al abrir:", value=float(val_ini), step=1.0)
        if st.button("ACTUALIZAR INICIAL"):
            datos["iniciales"][hoy][opcion] = nuevo_ini
            guardar_db(datos)
            st.rerun()

    st.divider()

    # --- REGISTRO DE PESO ---
    st.write(f"### ⚖️ Registro: {opcion}")
    pue = productos[opcion]
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        # Vinculado a session_state para permitir limpieza
        peso_total = st.number_input("Peso en Báscula:", 
                                     min_value=0.0,
                                     step=0.001,
                                     format="%.3f", 
                                     key="peso_input")
    with col_p2:
        t_cont = st.checkbox("Contenedor (.045)", key="t_cont")
        t_bisag = st.checkbox("Bisagra (0.016)", key="t_bisag")

    # Botones de Acción
    col_b1, col_b2 = st.columns(2)
    
    with col_b1:
        if st.button("REGISTRAR PESADA"):
            if peso_total > 0:
                tara_calc = (0.045 if t_cont else 0) + (0.016 if t_bisag else 0)
                p_neto = peso_total - (0.030 if "TINTA" in opcion else tara_calc)
                
                if p_neto > 0:
                    cant_res = p_neto / pue
                    
                    datos["historial"].append({
                        "fecha": hoy, 
                        "hora": datetime.now().strftime('%H:%M'), 
                        "art": opcion, 
                        "cant": round(cant_res, 2)
                    })
                    
                    if hoy not in datos["totales"]: datos["totales"][hoy] = {}
                    datos["totales"][hoy][opcion] = datos["totales"][hoy].get(opcion, 0.0) + cant_res
                    
                    guardar_db(datos)
                    st.success(f"Registrado: {cant_res:.2f} unidades")
                    limpiar_campos()
                    st.rerun()
                else:
                    st.error("Peso neto insuficiente (revisa la tara).")
            else:
                st.warning("Ingresa un peso válido.")

    with col_b2:
        if st.button("🧹 LIMPIAR"):
            limpiar_campos()
            st.rerun()

    # --- BALANCE VISUAL ---
    total_hoy = datos.get("totales", {}).get(hoy, {}).get(opcion, 0.0)
    saldo_final = max(0.0, val_ini - total_hoy)

    st.markdown(f"""
    <div class="resumen-caja">
        <div style="display:flex; justify-content:space-around; text-align:center; align-items:center;">
            <div><small>INICIAL</small><br><b class="metric-value">{val_ini:,.2f}</b></div>
            <div style="color:#e0d5a6;">−</div>
            <div><small>CONSUMO</small><br><b class="metric-value">{total_hoy:,.2f}</b></div>
            <div style="color:#e0d5a6;">=</div>
            <div><small>DISPONIBLE</small><br><b class="metric-total">{saldo_final:,.2f}</b></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- HISTORIAL Y CONTROL ---
st.divider()
col_h1, col_h2 = st.columns([2, 1])

with col_h1:
    if st.checkbox("Ver registros del día"):
        datos_h = cargar_db()
        h_hoy = datetime.now().strftime('%Y-%m-%d')
        df = pd.DataFrame([h for h in datos_h.get("historial", []) if h["fecha"] == h_hoy])
        if not df.empty:
            st.dataframe(df[["hora", "art", "cant"]], use_container_width=True)
        else:
            st.info("No hay registros hoy.")

with col_h2:
    if st.button("🗑️ REINICIAR DÍA"):
        datos_r = cargar_db()
        h_hoy = datetime.now().strftime('%Y-%m-%d')
        datos_r["totales"][h_hoy] = {}
        datos_r["historial"] = [h for h in datos_r["historial"] if h["fecha"] != h_hoy]
        guardar_db(datos_r)
        st.warning("Datos borrados")
        st.rerun()

st.caption("v2.8 | Champlitte - Sistema de Control de Insumos")
