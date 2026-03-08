import streamlit as st
import pandas as pd
from PIL import Image
import os
import sqlite3
from datetime import datetime
import urllib.parse

# ---------------- CONFIGURACIÓN DE PÁGINA ----------------
st.set_page_config(page_title="PUE Champlitte", page_icon="🍰", layout="centered")

# Inicializar contador de formulario para resetear campos
if "form_count" not in st.session_state:
    st.session_state.form_count = 0

# ---------------- CSS PERSONALIZADO ----------------
st.markdown("""
<style>
.stApp { background-color: #FFFFFF; }
.stApp, p, label, .stMarkdown, div[data-testid="stMarkdownContainer"] p { color: #000000 !important; }
header[data-testid="stHeader"], footer { visibility: hidden !important; height: 0; }
div.stButton > button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #fff2bd !important; color: #000000 !important; font-weight: bold; border: 1px solid #e0d5a6 !important; }
div[data-testid="stMetricValue"] { font-size: 45px; color: #000000 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------- LOGO ----------------
try:
    ruta_imagen = os.path.join(os.path.dirname(__file__), "champlitte.jpg")
    img = Image.open(ruta_imagen if os.path.exists(ruta_imagen) else "champlitte.jpg")
    st.image(img, width=120)
except:
    st.write("### PASTELERÍA CHAMPLITTE")

# ---------------- BASE DE DATOS ----------------
conn = sqlite3.connect("pue_champlitte.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS registros_pue (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha DATE, hora TIME, articulo TEXT, pue REAL, peso_total REAL, tara REAL, peso_neto REAL, resultado REAL)''')
conn.commit()

# ---------------- FUNCIONES ----------------
# NUEVO NÚMERO SOLICITADO
numero_whatsapp = "522283530069"

def reset_campos():
    st.session_state.form_count += 1

def enviar_whatsapp(texto):
    link = f"https://wa.me/{numero_whatsapp}?text={urllib.parse.quote(texto)}"
    st.markdown(f"**[📲 CLIC AQUÍ PARA ENVIAR A WHATSAPP]({link})**")

# ---------------- PRODUCTOS ----------------
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
    "TINTA EPSON 544 (CMYK) POR PZA A": 0.078,
    "AGUA CIEL 20 POR LT A": 1.0, "AZUCAR REFINADA POR KG A": 1.0,
    "BOLSA CAMISETA LOGO CH POR KG A": 1.0, "BOLSA CAMISETA LOGO GDE POR KG A": 1.0,
    "BOLSA NATURAL 18 X 25 POR KG A": 1.0, "PAPEL ENVOLTURA CHAMPLITTE POR KG M": 1.0,
    "ROLLO POLIPUNTEADO 25 X 35 POR KG B": 1.0, "BOLSA 90 X 120 POR KG A": 1.0,
    "BOLSA 60 X 90 POR KG M": 1.0, "CLOROLIMP POR L A": 1.0,
    "FIBRA PREGON P/BAÑO POR PZA M": 1.0, "FIBRA SCOTCH BRITE POR PZA A": 1.0,
    "FIBRA AZUL P/LAVAR CHAROLAS POR PZA B": 1.0, "JABON LIQUIDO PARA MANOS POR L M": 1.0,
    "LAVALOZA POR L A": 1.0, "PRO GEL POR L B": 1.0,
    "ROLLO TERMICO P/TPV POR PZA A": 1.0, "CUBETA POR PZA M": 1.0,
    "ESCOBA POR PZA A": 1.0, "ESCURRIDOR POR PZA M": 1.0,
    "RECOGEDOR POR PZA M": 1.0, "MECHUDO POR PZA A": 1.0,
}

# ---------------- TABS ----------------
tab1, tab2 = st.tabs(["📝 Calculadora PUE", "📊 Historial"])

with tab1:
    st.header("Calculadora PUE")
    
    # El sufijo del key cambia al resetear, limpiando el campo
    f_id = st.session_state.form_count
    
    modo_libre = st.checkbox("📝 Modo Libre", key=f"libre_{f_id}")
    
    if not modo_libre:
        opciones = sorted(list(productos.keys()))
        articulo = st.selectbox("Seleccione Artículo:", opciones, key=f"art_{f_id}")
        pue_final = productos.get(articulo, 0)
    else:
        articulo = st.text_input("Nombre del artículo manual:", key=f"name_{f_id}")
        pue_final = st.number_input("PUE Manual:", min_value=0.0, format="%.6f", key=f"pue_{f_id}")

    col1, col2 = st.columns(2)
    with col1:
        peso_total = st.number_input("Peso Total:", min_value=0.0, format="%.3f", key=f"peso_{f_id}")
    with col2:
        st.write("**Taras:**")
        t_cont = st.checkbox("Contenedor (.045)", key=f"c1_{f_id}")
        t_bisag = st.checkbox("Bisagra (0.16)", key=f"c2_{f_id}")
        tara_manual = st.number_input("Tara Manual:", min_value=0.0, format="%.4f", key=f"tm_{f_id}")

    if st.button("CALCULAR Y REGISTRAR"):
        if (pue_final > 0 or "TINTA" in articulo) and peso_total > 0:
            tara_total = (0.045 if t_cont else 0) + (0.16 if t_bisag else 0) + tara_manual
            peso_neto = peso_total - tara_total
            
            # Lógica especial Tinta
            if "TINTA EPSON" in articulo:
                resultado = (peso_neto - 0.03) / 0.078
            else:
                resultado = peso_neto / pue_final
            
            # Guardar en DB
            fecha_act = datetime.now().strftime("%Y-%m-%d")
            hora_act = datetime.now().strftime("%H:%M:%S")
            c.execute('INSERT INTO registros_pue (fecha,hora,articulo,pue,peso_total,tara,peso_neto,resultado) VALUES (?,?,?,?,?,?,?,?)',
                      (fecha_act, hora_act, articulo, pue_final, peso_total, tara_total, peso_neto, resultado))
            conn.commit()
            
            st.success(f"Registrado: {resultado:.2f}")
            enviar_whatsapp(f"PUE {articulo}\nResultado: {resultado:.2f}\nHora: {hora_act}")
            
            # Botón para limpiar campos después de ver el resultado
            st.button("LIMPIAR CAMPOS PARA NUEVO REGISTRO", on_click=reset_campos)
        else:
            st.error("Por favor ingrese Peso y Artículo válido.")

with tab2:
    st.header("Últimos Registros")
    df = pd.read_sql("SELECT * FROM registros_pue ORDER BY id DESC LIMIT 10", conn)
    st.dataframe(df[["hora", "articulo", "resultado"]], use_container_width=True)
    if st.button("Limpiar Historial"):
        c.execute("DELETE FROM registros_pue")
        conn.commit()
        st.rerun()
