import streamlit as st

import pandas as pd

from PIL import Image

import os

import json

from datetime import datetime, timedelta



# 1. CONFIGURACIÓN DE PÁGINA

st.set_page_config(page_title="PUE Champlitte v3.0", page_icon="🍰", layout="centered")



# 2. CSS: DISEÑO "CHAMPLITTE" (Texto blanco en inputs corregido)

st.markdown(

    """

    <style>

    .stApp { background-color: #FFFFFF; }

    h1, h2, h3, p, label, .stMarkdown, span { color: #000000 !important; }

    header[data-testid="stHeader"] { visibility: hidden !important; }



    /* INPUTS: FONDO OSCURO Y TEXTO BLANCO */

    input {

        color: #FFFFFF !important; 

        background-color: #333333 !important; 

        font-size: 20px !important;

        font-weight: bold !important;

        border-radius: 12px !important;

        border: 2px solid #000000 !important;

    }

    

    /* BOTONES CREMA */

    div.stButton > button {

        width: 100%;

        border-radius: 12px;

        height: 3.5em;

        background-color: #fff2bd !important;

        color: #000000 !important;

        font-weight: bold;

        border: 1px solid #e0d5a6 !important;

    }



    /* TABLAS */

    [data-testid="stTable"] {

        background-color: #f9f9f9;

        color: black !important;

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



# --- LOGO ---

try:

    st.image("champlitte.jpg", width=120)

except:

    st.write("### 🍰 PASTELERÍA CHAMPLITTE")



# 3. PRODUCTOS

productos = {

    "": 0,

    "BOLSA PAPEL CAFE #5 POR PQ/100 PZAS A": 0.832,

    "BOLSA PAPEL CAFE #6 POR PQ/100 PZAS A": 0.870,

    "BOLSA PAPEL CAFE #14 POR PQ/100 PZAS M": 1.364,

    "BOLSA PAPEL CAFE #20 POR PQ/100 PZAS M": 1.616,

    "CAJA TUTIS POR PZA A": 0.048,

    "TINTA EPSON 544 (CMYK) POR PZA A": 0.078,

    "AZUCAR REFINADA POR KG A": 1.0,

    "JABON LIQUIDO PARA MANOS POR L M": 1.0,

} # (Abreviado para el ejemplo, mantén tu lista completa)



opcion = st.selectbox("Selecciona Artículo:", sorted(list(productos.keys())), key="p_sel")



if opcion:

    db = cargar_db()

    hoy = datetime.now().strftime('%Y-%m-%d')

    

    # Asegurar llaves en el JSON

    if hoy not in db["iniciales"]: db["iniciales"][hoy] = {}

    if hoy not in db["totales"]: db["totales"][hoy] = {}



    # --- INVENTARIO INICIAL ---

    val_ini = db["iniciales"][hoy].get(opcion, 0.0)

    with st.expander("Ajustar Inventario Inicial"):

        n_ini = st.number_input("Cantidad inicial:", value=float(val_ini), key="n_ini")

        if st.button("Guardar Inicial"):

            db["iniciales"][hoy][opcion] = n_ini

            guardar_db(db)

            st.rerun()



  # --- PESAJE ---
    st.write(f"### ⚖️ Pesaje: {opcion}")
    col1, col2 = st.columns(2)
    
    with col1:
        p_total = st.number_input("Peso en Báscula:", value=None, placeholder="0.000", format="%.3f", key="peso_val")
    
    with col2:
        es_tinta = "TINTA" in opcion
        es_kilo = productos[opcion] == 1.0
        tara = 0.0
        
        if not es_tinta and not es_kilo:
            # Nueva sección de selección de Tara
            tipo_tara = st.radio(
                "Seleccionar Tara:",
                ["Sin Tara", "Bisagra (0.045)", "Contenedor (0.019)", "Personalizada"],
                horizontal=False
            )
            
            if tipo_tara == "Bisagra (0.045)":
                tara = 0.045
            elif tipo_tara == "Contenedor (0.019)":
                tara = 0.019
            elif tipo_tara == "Personalizada":
                tara = st.number_input("Peso Tara manual:", value=0.000, format="%.3f")
            else:
                tara = 0.0
        
        elif es_tinta:
            st.caption("Tara automática para Tinta: 0.030")
            tara = 0.030

# --- LÓGICA DEL BOTÓN REGISTRAR ---
if st.button("REGISTRAR PESADA"):
    if p_total is not None:
        pue = productos[opcion]
        # La tara ya fue definida arriba por la selección del usuario
        tara_aplicada = tara
        peso_ajustado = p_total - tara_aplicada
        divisor = 0.078 if es_tinta else (pue if pue != 0 else 1)
        
        if peso_ajustado >= 0:
            cantidad = round(peso_ajustado / divisor, 2)
            
            # --- EXPLICACIÓN DE LA OPERACIÓN ---
            st.info(f"""
            **Cálculo realizado:**
            * Peso Bruto: `{p_total:.3f}`
            * Tara aplicada: `- {tara_aplicada:.3f}`
            * Peso Neto: `{peso_ajustado:.3f}`
            * **Resultado: {cantidad} unidades**
            """)
            
            # Guardar en DB
            db = cargar_db() # Recargar para asegurar datos frescos
            db["historial"].append({
                "fecha": hoy, 
                "hora": datetime.now().strftime('%H:%M'),
                "art": opcion, 
                "cant": cantidad,
                "op": f"({p_total:.3f} - {tara_aplicada:.3f}) / {divisor}"
            })
            
            # Actualizar totales
            hoy_str = datetime.now().strftime('%Y-%m-%d')
            if hoy_str not in db["totales"]: db["totales"][hoy_str] = {}
            db["totales"][hoy_str][opcion] = db["totales"][hoy_str].get(opcion, 0.0) + cantidad
            
            guardar_db(db)
            st.success(f"Registrado con éxito")
            st.rerun()
        else:
            st.error("Error: El peso en báscula es menor que la tara seleccionada.")
