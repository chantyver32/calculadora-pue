import streamlit as st
import pandas as pd
from PIL import Image
import os
import json
from datetime import datetime

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="PUE Champlitte v3.0", page_icon="🍰", layout="centered")

# 2. CSS (Mantenemos tu estilo original)
st.markdown(
    """
    <style>
    .stApp { background-color: #FFFFFF; }
    h1, h2, h3, p, label, .stMarkdown, span { color: #000000 !important; }
    header[data-testid="stHeader"] { visibility: hidden !important; }
    input {
        color: #FFFFFF !important; 
        background-color: #333333 !important; 
        font-size: 20px !important;
        font-weight: bold !important;
        border-radius: 12px !important;
        border: 2px solid #000000 !important;
    }
    div.stButton > button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        background-color: #fff2bd !important;
        color: #000000 !important;
        font-weight: bold;
        border: 1px solid #e0d5a6 !important;
    }
    </style>
    """, 
    unsafe_allow_html=True
)

# --- MANEJO DE BASE DE DATOS ---
DB_FILE = "data_champlitte_v30.json"

def cargar_db():
    if not os.path.exists(DB_FILE):
        return {"historial": [], "totales": {}, "iniciales": {}}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {"historial": [], "totales": {}, "iniciales": {}}

def guardar_db(datos):
    with open(DB_FILE, "w") as f:
        json.dump(datos, f, indent=4)

# --- PRODUCTOS ---
productos = {
    "": 0,
    "MODO LIBRE (Escribir PUE)": -1,
    "BOLSA PAPEL CAFE #5 POR PQ/100 PZAS A": 0.832,
    "BOLSA PAPEL CAFE #6 POR PQ/100 PZAS A": 0.870,
    "BOLSA PAPEL CAFE #14 POR PQ/100 PZAS M": 1.364,
    "BOLSA PAPEL CAFE #20 POR PQ/100 PZAS M": 1.616,
    "CAJA TUTIS POR PZA A": 0.048,
    "TINTA EPSON 544 (CMYK) POR PZA A": 0.078,
    "AZUCAR REFINADA POR KG A": 1.0,
    "JABON LIQUIDO PARA MANOS POR L M": 1.0,
}

opcion = st.selectbox("Selecciona Artículo:", sorted(list(productos.keys())), key="p_sel")

if opcion:
    db = cargar_db()
    hoy = datetime.now().strftime('%Y-%m-%d')
    
    if hoy not in db["iniciales"]: db["iniciales"][hoy] = {}
    if hoy not in db["totales"]: db["totales"][hoy] = {}

    # --- LÓGICA MODO LIBRE ---
    pue_manual = 1.0
    nombre_final = opcion
    if opcion == "MODO LIBRE (Escribir PUE)":
        nombre_final = st.text_input("Nombre del producto libre:", value="Producto Genérico")
        pue_manual = st.number_input("Ingresa el PUE manual:", value=1.000, format="%.3f")
    else:
        pue_manual = productos[opcion]

    # --- PESAJE ---
    st.write(f"### ⚖️ Pesaje: {nombre_final}")
    col1, col2 = st.columns(2)
    
    with col1:
        p_total = st.number_input("Peso en Báscula:", value=None, placeholder="0.000", format="%.3f")

    with col2:
        # Selección de Tara con las nuevas opciones
        tara_tipo = st.radio("Seleccionar Tara:", ["Ninguna", "Bisagra (0.045)", "Contenedor (0.019)", "Manual"], horizontal=True)
        
        tara_valor = 0.0
        if tara_tipo == "Bisagra (0.045)":
            tara_valor = 0.045
        elif tara_tipo == "Contenedor (0.019)":
            tara_valor = 0.019
        elif tara_tipo == "Manual":
            tara_valor = st.number_input("Valor de Tara:", value=0.000, format="%.3f")

    # --- BOTÓN REGISTRAR ---
    if st.button("REGISTRAR PESADA"):
        if p_total is not None:
            divisor = pue_manual if pue_manual != 0 else 1
            peso_neto = p_total - tara_valor
            
            if peso_neto >= 0:
                cantidad = round(peso_neto / divisor, 2)
                
                # Explicación con 3 decimales en pesos y 2 en resultado
                st.info(f"""
                **Cálculo:**
                * Peso Bruto: `{p_total:.3f}` | Tara: `- {tara_valor:.3f}`
                * Peso Neto: `{peso_neto:.3f}` | PUE: `{divisor:.3f}`
                * **Resultado: {cantidad:.2f} unidades**
                """)
                
                # Guardar en DB
                db["historial"].append({
                    "fecha": hoy, 
                    "hora": datetime.now().strftime('%H:%M'),
                    "art": nombre_final, 
                    "cant": cantidad,
                    "op": f"({p_total:.3f} - {tara_valor:.3f}) / {divisor:.3f}"
                })
                db["totales"][hoy][nombre_final] = db["totales"][hoy].get(nombre_final, 0.0) + cantidad
                guardar_db(db)
                st.success("Registrado con éxito")
            else:
                st.error("Error: El peso en báscula es menor que la tara.")

# --- HISTORIAL ---
st.divider()
st.write("### 📋 Registros de Hoy")
db_view = cargar_db()
hoy_str = datetime.now().strftime('%Y-%m-%d')
hist = [h for h in db_view["historial"] if h["fecha"] == hoy_str]

if hist:
    df_hist = pd.DataFrame(hist)[["hora", "art", "cant", "op"]]
    df_hist.columns = ["Hora", "Artículo", "Cant (2 dec)", "Operación (3 dec)"]
    st.table(df_hist)
else:
    st.info("No hay registros hoy.")
