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

        tara = 0.0

        if not es_tinta and productos[opcion] != 1.0:

            if st.checkbox("¿Descontar Tara?"):

                tara = st.number_input("Peso Tara:", value=0.045, format="%.3f")



    if st.button("REGISTRAR PESADA"):

        if p_total:

            pue = productos[opcion]

            peso_ajustado = p_total - (0.030 if es_tinta else tara)

            divisor = 0.078 if es_tinta else pue

            

            if peso_ajustado >= 0:

                cantidad = round(peso_ajustado / divisor, 2)

                # Guardar

                db["historial"].append({

                    "fecha": hoy, "hora": datetime.now().strftime('%H:%M'),

                    "art": opcion, "cant": cantidad

                })

                db["totales"][hoy][opcion] = db["totales"][hoy].get(opcion, 0.0) + cantidad

                guardar_db(db)

                st.success(f"Registrado: {cantidad}")

                st.rerun()

            else:

                st.error("Error: El peso es menor a la tara.")



    # --- BALANCE ---

    total_hoy = db["totales"][hoy].get(opcion, 0.0)

    saldo = max(0.0, val_ini - total_hoy)

    st.metric("SALDO FINAL EN TIENDA", f"{saldo:,.2f}")



# --- HISTORIAL (Siempre visible al final) ---

st.divider()

st.write("### 📋 Registros de Hoy")

db_view = cargar_db()

hoy_str = datetime.now().strftime('%Y-%m-%d')

hist = [h for h in db_view["historial"] if h["fecha"] == hoy_str]



if hist:

    st.table(pd.DataFrame(hist)[["hora", "art", "cant"]])

else:

    st.info("No hay pesajes registrados hoy.")



if st.button("Reiniciar Todo"):

    guardar_db({"historial": [], "totales": {}, "iniciales": {}})

    st.rerun() 
