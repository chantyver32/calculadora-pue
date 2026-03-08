import streamlit as st
import pandas as pd
from PIL import Image
import os
import sqlite3
from datetime import datetime
import urllib.parse

# ---------------- CONFIGURACIÓN DE PÁGINA ----------------
st.set_page_config(page_title="PUE Champlitte", page_icon="🍰", layout="centered")

# ---------------- CSS PERSONALIZADO ----------------
st.markdown("""
<style>
.stApp { background-color: #FFFFFF; }
.stApp, p, label, .stMarkdown, div[data-testid="stMarkdownContainer"] p { color: #000000 !important; }
header[data-testid="stHeader"], footer { visibility: hidden !important; height: 0; }
div.stButton > button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #fff2bd !important; color: #000000 !important; font-weight: bold; border: 1px solid #e0d5a6 !important; transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);}
div.stButton > button:active { transform: scale(0.92); }
div.stButton > button:hover { border: 1px solid #000000 !important; background-color: #ffe88a !important; }
div[data-testid="stMetricValue"] { font-size: 45px; color: #000000 !important; }
.block-container { padding-top: 1.5rem !important; }
</style>
""", unsafe_allow_html=True)

# ---------------- LOGO ----------------
nombre_imagen = "champlitte.jpg"
ruta_actual = os.path.dirname(__file__)
ruta_imagen = os.path.join(ruta_actual, nombre_imagen)
try:
    if os.path.exists(ruta_imagen):
        img = Image.open(ruta_imagen)
    else:
        img = Image.open(nombre_imagen)
    st.image(img, width=120)
except:
    st.write("### PASTELERÍA CHAMPLITTE")

# ---------------- BASE DE DATOS ----------------
conn = sqlite3.connect("pue_champlitte.db", check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS registros_pue (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha DATE, hora TIME, articulo TEXT, pue REAL, peso_total REAL, tara REAL, peso_neto REAL, resultado REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS comparativa (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha DATE, hora TIME, articulo TEXT, resultado REAL, valor_usuario REAL, diferencia REAL)''')
conn.commit()

# ---------------- FUNCIONES ----------------
numero_whatsapp = "522283530069"

def limpiar_calculadora():
    st.session_state["peso_total"] = 0.0
    st.session_state["tara_contenedor"] = False
    st.session_state["tara_bisagra"] = False
    st.session_state["tara_manual"] = 0.0
    st.session_state["pue_libre"] = 0.0
    st.session_state["modo_libre"] = False
    st.session_state["articulo"] = ""

def enviar_whatsapp(texto):
    link = f"https://wa.me/{numero_whatsapp}?text={urllib.parse.quote(texto)}"
    st.markdown(f"[📲 Enviar a WhatsApp]({link})", unsafe_allow_html=True)

# ---------------- DICCIONARIO DE PRODUCTOS ACTUALIZADO ----------------
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
    "AGUA CIEL 20 POR LT A": 1.0,
    "AZUCAR REFINADA POR KG A": 1.0,
    "BOLSA CAMISETA LOGO CH POR KG A": 1.0,
    "BOLSA CAMISETA LOGO GDE POR KG A": 1.0,
    "BOLSA NATURAL 18 X 25 POR KG A": 1.0,
    "PAPEL ENVOLTURA CHAMPLITTE POR KG M": 1.0,
    "ROLLO POLIPUNTEADO 25 X 35 POR KG B": 1.0,
    "BOLSA 90 X 120 POR KG A": 1.0,
    "BOLSA 60 X 90 POR KG M": 1.0,
    "CLOROLIMP POR L A": 1.0,
    "FIBRA PREGON P/BAÑO POR PZA M": 1.0,
    "FIBRA SCOTCH BRITE POR PZA A": 1.0,
    "FIBRA AZUL P/LAVAR CHAROLAS POR PZA B": 1.0,
    "JABON LIQUIDO PARA MANOS POR L M": 1.0,
    "LAVALOZA POR L A": 1.0,
    "PRO GEL POR L B": 1.0,
    "ROLLO TERMICO P/TPV POR PZA A": 1.0,
    "CUBETA POR PZA M": 1.0,
    "ESCOBA POR PZA A": 1.0,
    "ESCURRIDOR POR PZA M": 1.0,
    "RECOGEDOR POR PZA M": 1.0,
    "MECHUDO POR PZA A": 1.0,
}

# ---------------- TABS ----------------
tab1, tab2, tab3 = st.tabs(["📝 Calculadora PUE", "📊 Comparativa / Ajuste", "⚠️ Administración"])

# ---------------- TAB 1: CALCULADORA ----------------
with tab1:
    st.header("Calculadora PUE")
    modo_libre = st.checkbox("📝 Modo Libre (Artículo no en lista)", key="modo_libre")
    
    if not modo_libre:
        opciones = sorted(list(productos.keys()))
        articulo = st.selectbox("Seleccione Artículo:", opciones, key="articulo")
        pue_final = productos.get(articulo, 0)
        es_tinta = (articulo == "TINTA EPSON 544 (CMYK) POR PZA A")
    else:
        pue_final = st.number_input("PUE Manual:", min_value=0.0, format="%.6f", step=0.001, key="pue_libre")
        articulo = "Entrada Manual"
        es_tinta = False
    
    col_a, col_b = st.columns(2)
    with col_a:
        peso_total = st.number_input("Peso Total:", min_value=0.0, format="%.3f", step=0.001, key="peso_total")
    with col_b:
        if not es_tinta:
            st.write("**Opciones de Tara:**")
            t_cont = st.checkbox("Contenedor (.045)", key="tara_contenedor")
            t_bisag = st.checkbox("Bisagra (0.16)", key="tara_bisagra")
            tara_manual = st.number_input("Tara Extra Manual", min_value=0.0, format="%.4f", step=0.0001, key="tara_manual")
        else:
            t_cont, t_bisag, tara_manual = False, False, 0.0

    if st.button("CALCULAR"):
        tara_total = (0.045 if t_cont else 0) + (0.16 if t_bisag else 0) + tara_manual
        peso_neto = peso_total - tara_total
        
        if peso_neto < 0:
            st.error("Error: La tara es mayor al peso total.")
        elif pue_final <= 0 and not es_tinta:
            st.warning("Seleccione un producto válido o ingrese un PUE.")
        else:
            if es_tinta:
                # Ajuste de 30g para envase de tinta según lógica previa
                resultado = (peso_neto - 0.03) / 0.078
            else:
                resultado = peso_neto / pue_final
            
            hora_act = datetime.now().strftime("%H:%M:%S")
            fecha_act = datetime.now().strftime("%Y-%m-%d")
            
            c.execute('INSERT INTO registros_pue (fecha,hora,articulo,pue,peso_total,tara,peso_neto,resultado) VALUES (?,?,?,?,?,?,?,?)',
                      (fecha_act, hora_act, articulo, pue_final, peso_total, tara_total, peso_neto, resultado))
            conn.commit()
            
            st.metric(label=f"Resultado ({hora_act})", value=f"{resultado:.2f}")
            enviar_whatsapp(f"Registro PUE:\nArt: {articulo}\nNeto: {peso_neto:.3f}\nRes: {resultado:.2f}")

    st.button("LIMPIAR TODO", on_click=limpiar_calculadora)

# ---------------- TAB 2: COMPARATIVA ----------------
with tab2:
    st.header("Comparativa")
    df = pd.read_sql("SELECT * FROM registros_pue ORDER BY id DESC", conn)
    if not df.empty:
        st.dataframe(df[["fecha", "hora", "articulo", "resultado"]], use_container_width=True)
        articulo_sel = st.selectbox("Comparar artículo:", df["articulo"].unique())
        valor_fisico = st.number_input("Cantidad física actual:", min_value=0.0)
        
        if st.button("Calcular Diferencia"):
            val_sistema = df[df["articulo"] == articulo_sel].iloc[0]["resultado"]
            dif = val_sistema - valor_fisico
            st.metric("Diferencia", f"{dif:.2f}")
            enviar_whatsapp(f"Comparativa: {articulo_sel}\nSistema: {val_sistema:.2f}\nFísico: {valor_fisico:.2f}\nDif: {dif:.2f}")
    else:
        st.info("Sin registros para comparar.")

# ---------------- TAB 3: RESET ----------------
with tab3:
    if st.checkbox("Confirmar borrado total"):
        if st.button("BORRAR BASE DE DATOS"):
            c.execute("DELETE FROM registros_pue")
            c.execute("DELETE FROM comparativa")
            conn.commit()
            st.success("Limpieza completada.")
            st.rerun()
