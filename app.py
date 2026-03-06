import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="PUE Champlitte v3.0", page_icon="🍰", layout="centered")

# 2. CSS: DISEÑO "CHAMPLITTE"
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

# --- LOGO / TÍTULO ---
st.write("### 🍰 PASTELERÍA CHAMPLITTE - PUE v3.0")

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
}

opcion = st.selectbox("Selecciona Artículo:", sorted(list(productos.keys())), key="p_sel")

if opcion:
    db = cargar_db()
    hoy = datetime.now().strftime('%Y-%m-%d')
    
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
        p_total = st.number_input("Peso en Báscula:", value=0.000, format="%.3f", key="peso_val")
    
    with col2:
        es_tinta = "TINTA" in opcion
        usar_tara = False
        p_tara = 0.000
        
        if es_tinta:
            p_tara = 0.030
            st.caption("Tara fija Tinta: 0.030")
        elif productos[opcion] != 1.0:
            usar_tara = st.checkbox("¿Descontar Tara?")
            if usar_tara:
                p_tara = st.number_input("Peso Tara:", value=0.045, format="%.3f")

    # --- LÓGICA DE CÁLCULO ---
    pue = productos[opcion]
    peso_neto = p_total - p_tara
    
    if p_total > 0:
        if peso_neto < 0:
            st.error("📢 El peso total no puede ser menor a la tara.")
        elif pue == 0:
            st.warning("⚠️ Este artículo no tiene un factor PUE definido.")
        else:
            # Definir fórmula y resultado
            # Si es tinta, el divisor es 0.078 fijo por lógica previa
            divisor = 0.078 if es_tinta else pue
            resultado = round(peso_neto / divisor, 2)
            txt_formula = f"({p_total:.3f} - {p_tara:.3f}) / {divisor}"

            # Mostrar Memoria de Cálculo arriba de la tabla/botón
            st.info(f"**Operación:** {txt_formula} = **{resultado}**")

            if st.button("REGISTRAR PESADA"):
                # Guardar en Historial
                db["historial"].append({
                    "fecha": hoy, 
                    "hora": datetime.now().strftime('%H:%M'),
                    "art": opcion, 
                    "operacion": txt_formula,
                    "cant": resultado
                })
                # Actualizar Totales
                db["totales"][hoy][opcion] = db["totales"][hoy].get(opcion, 0.0) + resultado
                guardar_db(db)
                st.success(f"Registrado: {resultado}")
                st.rerun()

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
    # Se añade la columna 'operacion' a la vista de la tabla
    df_hist = pd.DataFrame(hist)
    st.table(df_hist[["hora", "art", "operacion", "cant"]])
else:
    st.info("No hay pesajes registrados hoy.")

if st.button("Reiniciar Todo"):
    guardar_db({"historial": [], "totales": {}, "iniciales": {}})
    st.rerun()
