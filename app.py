import streamlit as st
import pandas as pd
from PIL import Image
import os
import sqlite3
from datetime import datetime
import urllib.parse

# ---------------- CONFIGURACIÓN ----------------
st.set_page_config(page_title="PUE Champlitte", page_icon="🍰", layout="centered")

# Inicializar estados si no existen
if "resultado_pue" not in st.session_state:
    st.session_state.resultado_pue = None
if "enlace_wa" not in st.session_state:
    st.session_state.enlace_wa = None

# ---------------- CSS ----------------
st.markdown("""
<style>
.stApp { background-color: #FFFFFF; }
.stApp, p, label, .stMarkdown, div[data-testid="stMarkdownContainer"] p { color: #000000 !important; }
div.stButton > button { width: 100%; border-radius: 12px; height: 3em; background-color: #fff2bd !important; font-weight: bold; border: 1px solid #e0d5a6 !important; }
div[data-testid="stMetricValue"] { font-size: 40px; color: #000000 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------- BASE DE DATOS ----------------
conn = sqlite3.connect("pue_champlitte.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS registros_pue (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha DATE, hora TIME, articulo TEXT, resultado REAL)''')
conn.commit()

# ---------------- PRODUCTOS ----------------
productos = {
    "": 0, "BOLSA PAPEL CAFE #5": 0.832, "BOLSA PAPEL CAFE #6": 0.870, "BOLSA PAPEL CAFE #14": 1.364,
    "BOLSA PAPEL CAFE #20": 1.616, "CAJA TUTIS": 0.048, "CAPACILLO CHINO": 0.00104,
    "CAPACILLO ROJO #72": 0.000436, "CONT BISAG P/5-6 TUTIS": 0.014, "CUCHARA MED DESCH": 0.00165,
    "ETIQUETA 4 X 4": 0.000328, "ETIQUETA 6 X 6": 0.00057, "EMPLAYE GRANDE ROLLO": 1.174,
    "PAPEL ALUMINIO": 1.342, "SERVILLETA PQ/500": 0.001192, "COFIA PQ/100": 0.238,
    "GUANTES POLIURETANO": 0.086, "HIGIENICO SCOTT": 0.500, "TOALLA ROLLO 180M": 1.115,
    "BOLSA LOCK": 0.018, "CAJA DE GRAPAS": 0.176, "CINTA EMPAQUE": 0.272, "CINTA DELIMITADORA": 0.346,
    "COMPROBANTE TRASLADO": 0.0086, "ETIQUETA BLANCA 13X19": 0.050, "HOJAS BLANCAS PQ/500": 2.146,
    "TINTA EPSON 544": 0.078, "AGUA CIEL 20 LT": 1.0, "AZUCAR REFINADA": 1.0,
    "BOLSA CAMISETA CH": 1.0, "BOLSA CAMISETA GDE": 1.0, "BOLSA NATURAL 18X25": 1.0,
    "PAPEL ENVOLTURA": 1.0, "ROLLO POLIPUNTEADO": 1.0, "BOLSA 90X120": 1.0, "BOLSA 60X90": 1.0,
    "CLOROLIMP": 1.0, "FIBRA PREGON": 1.0, "FIBRA SCOTCH BRITE": 1.0, "FIBRA AZUL": 1.0,
    "JABON MANOS": 1.0, "LAVALOZA": 1.0, "PRO GEL": 1.0, "ROLLO TERMICO": 1.0, "CUBETA": 1.0,
    "ESCOBA": 1.0, "ESCURRIDOR": 1.0, "RECOGEDOR": 1.0, "MECHUDO": 1.0
}

# ---------------- APP ----------------
st.title("🍰 PUE Champlitte")

with st.form("pue_form", clear_on_submit=True):
    articulo_sel = st.selectbox("Seleccione Artículo:", sorted(productos.keys()))
    peso_t = st.number_input("Peso Total (kg):", min_value=0.0, step=0.001, format="%.3f")
    
    col1, col2 = st.columns(2)
    with col1:
        t_cont = st.checkbox("Contenedor (.045)")
        t_bis = st.checkbox("Bisagra (0.16)")
    with col2:
        t_man = st.number_input("Tara Manual:", min_value=0.0, step=0.001, format="%.3f")
    
    submit = st.form_submit_button("CALCULAR Y REGISTRAR")

if submit:
    pue_val = productos.get(articulo_sel, 0)
    if (pue_val > 0 or "TINTA" in articulo_sel) and peso_t > 0:
        tara_total = (0.045 if t_cont else 0) + (0.16 if t_bis else 0) + t_man
        peso_neto = peso_t - tara_total
        
        # Lógica especial Tinta
        if "TINTA" in articulo_sel:
            res = (peso_neto - 0.03) / 0.078
        else:
            res = peso_neto / pue_val
            
        # Guardar en DB
        h_act = datetime.now().strftime("%H:%M:%S")
        f_act = datetime.now().strftime("%Y-%m-%d")
        c.execute('INSERT INTO registros_pue (fecha, hora, articulo, resultado) VALUES (?,?,?,?)', (f_act, h_act, articulo_sel, res))
        conn.commit()
        
        # Guardar resultados en session_state para mostrar fuera del form
        st.session_state.resultado_pue = f"{res:.2f}"
        msg = f"Registro PUE\nArt: {articulo_sel}\nResultado: {res:.2f}\nHora: {h_act}"
        st.session_state.enlace_wa = f"https://wa.me/522281348454?text={urllib.parse.quote(msg)}"
    else:
        st.error("Datos incompletos.")

# Mostrar Resultados
if st.session_state.resultado_pue:
    st.divider()
    st.metric("Resultado Final", st.session_state.resultado_pue)
    st.markdown(f"### [📲 ENVIAR A WHATSAPP]({st.session_state.enlace_wa})")
    if st.button("LIMPIAR PANTALLA"):
        st.session_state.resultado_pue = None
        st.rerun()

st.divider()
st.subheader("Historial Hoy")
try:
    df = pd.read_sql("SELECT hora, articulo, resultado FROM registros_pue ORDER BY id DESC LIMIT 5", conn)
    st.table(df)
except:
    st.write("No hay registros.")
