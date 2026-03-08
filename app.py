import streamlit as st
from PIL import Image
import os
import sqlite3
from datetime import datetime
import urllib.parse

# ---------------- CONFIGURACIÓN DE PÁGINA ----------------
st.set_page_config(page_title="PUE Champlitte", page_icon="🍰", layout="centered")

# ---------------- CSS ----------------
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

c.execute('''
CREATE TABLE IF NOT EXISTS registros_pue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE,
    hora TIME,
    articulo TEXT,
    pue REAL,
    peso_total REAL,
    tara REAL,
    peso_neto REAL,
    resultado REAL
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS comparativa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE,
    hora TIME,
    articulo TEXT,
    resultado REAL,
    valor_usuario REAL,
    diferencia REAL
)
''')
conn.commit()

# ---------------- FUNCIONES ----------------
numero_whatsapp = "522283530069"

def limpiar_calculadora():
    st.session_state["peso_total"] = None
    st.session_state["tara_contenedor"] = False
    st.session_state["tara_bisagra"] = False
    st.session_state["tara_manual"] = None
    st.session_state["pue_libre"] = 0.0
    st.session_state["modo_libre"] = False
    st.session_state["articulo"] = ""
    st.session_state["resultado_calc"] = None

def enviar_whatsapp(texto):
    link = f"https://wa.me/{numero_whatsapp}?text={urllib.parse.quote(texto)}"
    st.markdown(f"[📲 Enviar a WhatsApp]({link})", unsafe_allow_html=True)

# ---------------- PRODUCTOS ----------------
productos = {
    "": 0,
    "BOLSA PAPEL CAFE #5 POR PQ/100 PZAS A": 0.832,
    "BOLSA PAPEL CAFE #6 POR PQ/100 PZAS A": 0.870,
    "BOLSA PAPEL CAFE #14 POR PQ/100 PZAS M": 1.364,
    "CAJA TUTIS POR PZA A": 0.048,
    "CAPACILLO CHINO POR PZA B": 0.00104,
    "TINTA EPSON 544 (CMYK) POR PZA A": 0.078,
    "AGUA CIEL 20 POR LT A": 1.0,
    "AZUCAR REFINADA POR KG A": 1.0
}

# ---------------- TABS ----------------
tab1, tab2, tab3 = st.tabs(["📝 Calculadora PUE", "📊 Comparativa / Ajuste", "⚠️ Administración / Reset"])

# ---------------- TAB 1: CALCULADORA ----------------
with tab1:
    st.header("Calculadora PUE")
    modo_libre = st.checkbox("📝 Modo Libre (Artículo no registrado)", key="modo_libre")
    
    if not modo_libre:
        opciones = sorted(list(productos.keys()))
        articulo = st.selectbox("Artículo:", opciones, key="articulo")
        pue_final = productos.get(articulo,0)
        es_tinta = (articulo == "TINTA EPSON 544 (CMYK) POR PZA A")
    else:
        pue_final = st.number_input("PUE Libre:", min_value=0.0, format="%.6f", step=0.001, key="pue_libre")
        articulo = "Manual"
        es_tinta = False
    
    col_a, col_b = st.columns(2)
    with col_a:
        peso_total = st.number_input("Peso Total:", min_value=0.0, format="%.3f", step=0.001, key="peso_total")
    with col_b:
        if not es_tinta:
            st.write("**Opciones de Tara:**")
            t_cont = st.checkbox("Contenedor (.045)", key="tara_contenedor")
            t_bisag = st.checkbox("Bisagra (0.16)", key="tara_bisagra")
            tara_manual = st.number_input("Tara Manual", min_value=0.0, format="%.4f", step=0.0001, key="tara_manual")
        else:
            t_cont = False
            t_bisag = False
            tara_manual = 0.0

    btn_calcular = st.button("CALCULAR")
    st.button("LIMPIAR", on_click=limpiar_calculadora)

    if btn_calcular:
        tara_total = 0.0
        if t_cont: tara_total += 0.045
        if t_bisag: tara_total += 0.16
        tara_total += tara_manual
        peso_neto = peso_total - tara_total
        if peso_neto < 0:
            st.error("La tara es mayor al peso total.")
        else:
            if es_tinta:
                peso_neto -= 0.03
                resultado = peso_neto / 0.078
            else:
                resultado = peso_neto / pue_final if pue_final>0 else None
            if resultado is not None:
                hora_actual = datetime.now().strftime("%H:%M:%S")
                fecha_actual = datetime.now().strftime("%Y-%m-%d")
                # Guardar en DB
                c.execute('INSERT INTO registros_pue (fecha,hora,articulo,pue,peso_total,tara,peso_neto,resultado) VALUES (?,?,?,?,?,?,?,?)',
                          (fecha_actual,hora_actual,articulo,pue_final,peso_total,tara_total,peso_neto,resultado))
                conn.commit()
                st.metric(label=f"Resultado (Hora {hora_actual})", value=f"{resultado:.2f}")
                st.caption(f"Tara total: {tara_total:.4f}")
                # WhatsApp
                enviar_whatsapp(f"Registro PUE:\nArtículo: {articulo}\nPeso Total: {peso_total}\nTara: {tara_total}\nPeso Neto: {peso_neto}\nResultado: {resultado:.2f}\nHora: {hora_actual}")

# ---------------- TAB 2: COMPARATIVA ----------------
with tab2:
    st.header("Comparativa / Ajuste")
    df = st.read_sql("SELECT * FROM registros_pue ORDER BY id DESC", conn)
    if df.empty:
        st.info("No hay registros aún.")
    else:
        st.dataframe(df[["fecha","hora","articulo","resultado"]], use_container_width=True)
        articulo_sel = st.selectbox("Seleccionar artículo para comparativa", df["articulo"].unique())
        valor_usuario = st.number_input("Valor a comparar:", min_value=0.0, format="%.2f")
        btn_comparar = st.button("Calcular Diferencia")
        if btn_comparar:
            df_sel = df[df["articulo"]==articulo_sel].iloc[0]
            diferencia = df_sel["resultado"] - valor_usuario
            fecha_actual = datetime.now().strftime("%Y-%m-%d")
            hora_actual = datetime.now().strftime("%H:%M:%S")
            c.execute('INSERT INTO comparativa (fecha,hora,articulo,resultado,valor_usuario,diferencia) VALUES (?,?,?,?,?,?)',
                      (fecha_actual,hora_actual,articulo_sel,df_sel["resultado"],valor_usuario,diferencia))
            conn.commit()
            st.metric(label=f"Diferencia (Hora {hora_actual})", value=f"{diferencia:.2f}")
            # WhatsApp
            enviar_whatsapp(f"Comparativa:\nArtículo: {articulo_sel}\nResultado: {df_sel['resultado']:.2f}\nValor Usuario: {valor_usuario}\nDiferencia: {diferencia:.2f}\nHora: {hora_actual}")

# ---------------- TAB 3: RESET ----------------
with tab3:
    st.header("Administración / Reset")
    st.write("⚠️ Esta acción borrará todos los registros.")
    confirm_reset = st.checkbox("Confirmar que deseo borrar todo", key="check_reset")
    if st.button("⚠️ EJECUTAR RESET TOTAL"):
        if confirm_reset:
            c.execute("DELETE FROM registros_pue")
            c.execute("DELETE FROM comparativa")
            conn.commit()
            st.success("✅ Base de datos limpiada.")
        else:
            st.error("Debes confirmar la casilla para poder borrar.")
