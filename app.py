import streamlit as st
import pandas as pd
from PIL import Image
import os
import json
from datetime import datetime

# 1. Configuración de página
st.set_page_config(page_title="PUE Champlitte v1.2", page_icon="🍰", layout="centered")

# 2. CSS Optimizado (Basado en tu diseño v1.1)
st.markdown(
    """
    <style>
    .stApp { background-color: #FFFFFF; }
    .stApp, p, label, .stMarkdown, div[data-testid="stMarkdownContainer"] p {
        color: #000000 !important;
    }
    header[data-testid="stHeader"], footer {
        visibility: hidden !important;
        height: 0;
    }
    /* Estilo para los botones */
    div.stButton > button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        background-color: #fff2bd !important;
        color: #000000 !important;
        font-weight: bold;
        border: 1px solid #e0d5a6 !important;
        transition: all 0.2s ease;
    }
    div.stButton > button:active { transform: scale(0.95); }
    div.stButton > button:hover {
        border: 1px solid #000000 !important;
        background-color: #ffe88a !important;
    }
    /* Quitar cursor en selectbox para móviles */
    div[data-baseweb="select"] input { caret-color: transparent !important; }

    /* Ajuste de métricas */
    div[data-testid="stMetricValue"] { 
        font-size: 48px; 
        color: #D4A017 !important; 
    }
    .block-container { padding-top: 1.5rem !important; }
    
    /* Estilo de la tabla */
    .stDataFrame { border: 1px solid #e0d5a6; border-radius: 10px; }
    </style>
    """, 
    unsafe_allow_html=True
)

# --- BASE DE DATOS LOCAL (Session State) ---
if "historial" not in st.session_state:
    st.session_state.historial = []

# --- CARGA DE LOGO ---
try:
    st.image("champlitte.jpg", width=120)
except:
    st.write("### 🍰 PASTELERÍA CHAMPLITTE")

# 3. Diccionario de productos
productos = {
    "": 0,
    "BOLSA PAPEL CAFE #5 POR PQ/100 PZAS A": 0.832,
    "BOLSA PAPEL CAFE #6 POR PQ/100 PZAS A": 0.870,
    "BOLSA PAPEL CAFE #14 POR PQ/100 PZAS M": 1.364,
    "BOLSA PAPEL CAFE #20 POR PQ/100 PZAS M": 1.616,
    "CAJA TUTIS POR PZA A": 0.048,
    "CAPACILLO CHINO POR PZA B": 0.00104,
    "CAPACILLO ROJO #72 POR PZA A": 0.000436,
    "CONT BISAG P/5-6 TUTIS POR PZA A": 0.014,
    "CUCHARA MED DESCH POR PZA A": 0.00165,
    "ETIQUETA CHAMPLITTE CHICA 4 X 4 POR PZA B": 0.000328,
    "ETIQUETA CHAMPLITTE MEDIANA 6 X 6 POR PZA B": 0.00057,
    "EMPLAYE GRANDE ROLLO POR PZA T": 1.174,
    "PAPEL ALUMINIO POR PZA T": 1.342,
    "SERVILLETA PQ/500 HJ POR PZA A": 0.001192,
    "COFIA POR PQ/100 PZAS A": 0.238,
    "GUANTES TRANSP POLIURETANO POR PQ/100 PZAS A": 0.086,
    "HIGIENICO SCOTT ROLLO POR PZA M": 0.500,
    "TOALLA ROLLO 180M POR PZA M": 1.115,
    "BOLSA LOCK POR PZA A": 0.018,
    "CAJA DE GRAPAS POR PZA M": 0.176,
    "CINTA TRANSP EMPAQUE POR PZA M": 0.272,
    "CINTA DELIMITADORA POR PZA B": 0.346,
    "COMPROBANTE TRASLADO VALORES POR PZA A": 0.0086,
    "ETIQUETA BLANCA ADH 13 X 19 POR PQ M": 0.050,
    "HOJAS BLANCAS PQ/500 POR PZA A": 2.146,
    "TINTA EPSON 544 (CMYK) POR PZA A": 0.078
}

def limpiar_pantalla():
    st.session_state["peso_input"] = None
    st.session_state["tara_input"] = None
    st.session_state["activar_tara"] = False
    st.session_state["producto_sel"] = ""

# --- INTERFAZ ---
st.write("## Calculadora de PUE")

opcion = st.selectbox("Selecciona el Artículo:", sorted(list(productos.keys())), key="producto_sel")
es_tinta = (opcion == "TINTA EPSON 544 (CMYK) POR PZA A")

col_a, col_b = st.columns(2)
with col_a:
    peso_total = st.number_input("Peso Total (kg):", format="%.3f", step=0.001, value=None, placeholder="0.000", key="peso_input")

with col_b:
    if not es_tinta:
        usar_tara = st.checkbox("¿Descontar Tara?", key="activar_tara")
        peso_tara = st.number_input("Peso Tara (kg):", format="%.4f", step=0.0001, value=None, placeholder="0.0000", key="tara_input") if usar_tara else 0.0
    else:
        st.info("💡 Tara de envase (0.030) auto.")
        peso_tara = 0.030
        usar_tara = True

st.write("") 

col1, col2 = st.columns([3, 1])
btn_registrar = col1.button("REGISTRAR PESADA")
col2.button("LIMPIAR", on_click=limpiar_pantalla)

# --- LÓGICA DE CÁLCULO ---
if btn_registrar:
    if not opcion:
        st.warning("⚠️ Selecciona un artículo.")
    elif peso_total is None:
        st.warning("⚠️ Ingresa el peso.")
    else:
        pue = productos[opcion]
        peso_neto = peso_total - peso_tara
        
        if peso_neto < 0:
            st.error("📢 Peso insuficiente.")
        else:
            # Cálculo
            if es_tinta:
                resultado = (peso_total - 0.030) / 0.078
            else:
                resultado = peso_neto / pue if pue > 0 else 0
            
            # Guardar en historial
            nuevo_registro = {
                "Hora": datetime.now().strftime("%H:%M:%S"),
                "Artículo": opcion,
                "Peso Total": f"{peso_total:.3f}",
                "Tara": f"{peso_tara:.4f}",
                "Cantidad (PUE)": round(resultado, 2)
            }
            st.session_state.historial.insert(0, nuevo_registro)
            
            st.metric(label="Resultado Actual", value=f"{resultado:.2f}")
            st.success("✅ Registrado en la tabla inferior.")

# --- TABLA DE CONSULTA ---
st.markdown("---")
st.write("### 📋 Historial de Pesajes (Hoy)")

if st.session_state.historial:
    df = pd.DataFrame(st.session_state.historial)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    col_csv, col_del = st.columns(2)
    # Descargar datos
    csv = df.to_csv(index=False).encode('utf-8')
    col_csv.download_button("📥 DESCARGAR REPORTE", csv, "reporte_champlitte.csv", "text/csv")
    
    # Reiniciar tabla
    if col_del.button("🗑️ REINICIAR TABLA"):
        st.session_state.historial = []
        st.rerun()
else:
    st.info("No hay registros todavía.")

st.caption("v1.2 - Champlitte 2026 | Sistema de Control de Insumos")
