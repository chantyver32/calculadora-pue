import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="PUE Champlitte v2.9", page_icon="🍰", layout="centered")

# 2. CSS MEJORADO
st.markdown(
    """
    <style>
    .stApp { background-color: #FFFFFF; }
    h1, h2, h3, p, label, .stMarkdown, span { color: #000000 !important; }
    header[data-testid="stHeader"] { visibility: hidden; }

    /* Estilo de los Inputs */
    input {
        color: #FFFFFF !important; 
        background-color: #444444 !important;
        font-size: 20px !important;
        font-weight: bold !important;
        border-radius: 10px !important;
        border: 2px solid #b08d15 !important;
    }
    
    /* Botones */
    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        background-color: #fff2bd !important;
        color: #000000 !important;
        font-weight: bold;
        border: 1px solid #e0d5a6 !important;
    }
    </style>
    """, 
    unsafe_allow_html=True
)

# --- LÓGICA DE BASE DE DATOS ---
DB_FILE = "data_champlitte_v29.json"

def cargar_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {"historial": [], "totales": {}, "iniciales": {}}
    return {"historial": [], "totales": {}, "iniciales": {}}

def guardar_db(datos):
    with open(DB_FILE, "w") as f: json.dump(datos, f, indent=4)

datos = cargar_db()
hoy = datetime.now().strftime('%Y-%m-%d')
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

# --- CREACIÓN DE PESTAÑAS ---
tab_registro, tab_resumen = st.tabs(["⚖️ REGISTRO DE PESO", "📋 CORTE DEL DÍA"])

# --- PESTAÑA 1: REGISTRO ---
with tab_registro:
    if os.path.exists("champlitte.jpg"):
        st.image("champlitte.jpg", width=100)
    
    if st.button("🔄 LIMPIAR PARA OTRO PRODUCTO"):
        st.session_state.p_sel = ""
        st.rerun()

    opcion = st.selectbox("ARTÍCULO:", sorted(list(productos.keys())), key="p_sel")

    if opcion != "":
        # Manejo de Inventario Inicial
        if hoy not in datos["iniciales"]: datos["iniciales"][hoy] = {}
        if opcion not in datos["iniciales"][hoy]:
            ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            ini_ayer = datos.get("iniciales", {}).get(ayer, {}).get(opcion, 0.0)
            tot_ayer = datos.get("totales", {}).get(ayer, {}).get(opcion, 0.0)
            datos["iniciales"][hoy][opcion] = max(0.0, ini_ayer - tot_ayer)
            guardar_db(datos)

        pue = productos[opcion]
        
        col1, col2 = st.columns(2)
        with col1:
            peso_total = st.number_input("Peso Báscula:", value=0.0, format="%.3f")
        with col2:
            tara = st.radio("Tara:", ["Ninguna", "Contenedor (0.045)", "Bisagra (0.016)"])
        
        if st.button("REGISTRAR"):
            if peso_total > 0:
                tara_val = 0.045 if "Cont" in tara else (0.016 if "Bis" in tara else 0)
                p_neto = peso_total - (0.030 if "TINTA" in opcion else tara_val)
                
                if p_neto > 0:
                    cant_res = p_neto / pue
                    datos["historial"].append({"fecha": hoy, "art": opcion, "cant": round(cant_res, 2)})
                    if hoy not in datos["totales"]: datos["totales"][hoy] = {}
                    datos["totales"][hoy][opcion] = datos["totales"][hoy].get(opcion, 0.0) + cant_res
                    guardar_db(datos)
                    st.success(f"Registrado correctamente.")
                    st.rerun()

# --- PESTAÑA 2: RESUMEN DEL DÍA ---
with tab_resumen:
    st.subheader(f"Resumen General - {hoy}")
    
    # Filtrar historial de hoy
    df_h = pd.DataFrame(datos.get("historial", []))
    
    # Mostrar tabla detallada de todos los productos que han tenido movimiento
    resumen_list = []
    lista_articulos = datos["iniciales"].get(hoy, {}).keys()
    
    for art in lista_articulos:
        p_ini = datos["iniciales"][hoy].get(art, 0.0)
        p_hoy = datos["totales"].get(hoy, {}).get(art, 0.0)
        if p_ini > 0 or p_hoy > 0:
            resumen_list.append({
                "PRODUCTO": art,
                "INICIAL": round(p_ini, 2),
                "CONSUMIDO": round(p_hoy, 2),
                "DISPONIBLE": round(p_ini - p_hoy, 2)
            })

    if resumen_list:
        st.table(pd.DataFrame(resumen_list))
        
        if st.button("🗑️ REINICIAR DÍA (BORRAR TODO)"):
            datos["totales"][hoy] = {}
            datos["historial"] = [h for h in datos["historial"] if h["fecha"] != hoy]
            guardar_db(datos)
            st.rerun()
    else:
        st.info("Aún no hay movimientos registrados hoy.")

st.caption("v2.9 | Champlitte - Control de Insumos")
