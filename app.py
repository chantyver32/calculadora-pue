import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import urllib.parse
import pytz
import io
import time
import speech_recognition as sr
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ROW_HEIGHT_RULE
import re
import streamlit.components.v1 as components

# 1. CONFIGURACIÓN Y ESTADO
st.set_page_config(page_title="PUE Champlitte Pro", layout="wide", page_icon="⚖️")

# Estilos CSS
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .btn-wa {
        background-color: #25D366;
        color: white !important;
        padding: 10px 20px;
        text-align: center;
        text-decoration: none !important;
        display: block;
        font-size: 14px;
        font-weight: bold;
        border-radius: 8px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .btn-wa:hover { background-color: #128C7E; }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #1f77b4; }
    </style>
""", unsafe_allow_html=True)

# 2. BASE DE DATOS (Conexión persistente corregida)
def get_connection():
    return sqlite3.connect("pue_champlitte_v4.db", check_same_thread=False)

conn = get_connection()
c = conn.cursor()

# Crear tablas si no existen
c.execute('''CREATE TABLE IF NOT EXISTS pesajes_individuales 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_hora TEXT, articulo TEXT, 
             peso_bruto REAL, tara REAL, pue REAL, resultado_pue REAL, detalle_formula TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS pesajes_guardados 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_hora TEXT, articulo TEXT, 
             peso_bruto REAL, tara REAL, pue REAL, resultado_pue REAL, detalle_formula TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS auditoria_stock 
             (articulo TEXT PRIMARY KEY, total_real REAL, stock REAL, diferencia REAL)''')
conn.commit()

# --- FUNCIONES DE FORMATO ---
def truncar_dos_decimales(valor):
    if valor is None: return 0.0
    return int(valor * 100) / 100.0

def formato_estricto(valor):
    if pd.isna(valor) or valor is None: return "0.00"
    return f"{float(valor):.2f}"

def generar_word_tarjetas(df):
    doc = Document()
    for section in doc.sections:
        section.top_margin = Cm(1)
        section.bottom_margin = Cm(1)
        section.left_margin = Cm(1)
        section.right_margin = Cm(1)
    
    cols = 4
    rows = (len(df) + cols - 1) // cols
    if rows == 0: rows = 1
    
    table = doc.add_table(rows=rows, cols=cols)
    table.style = 'Table Grid'
    
    for idx, row_data in df.iterrows():
        r = idx // cols
        c_idx = idx % cols
        cell = table.cell(r, c_idx)
        
        # Ajuste de tamaño de celda
        cell.width = Cm(5)
        table.rows[r].height = Cm(2)
        
        articulo = str(row_data['articulo'])
        resultado = formato_estricto(row_data['resultado_pue'])
        
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run1 = p.add_run(f"\n{articulo}\n")
        run1.font.size = Pt(8)
        run1.bold = True
        
        run2 = p.add_run(f"Total: {resultado}")
        run2.font.size = Pt(12)
        run2.bold = True

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# 3. DICCIONARIO DE PRODUCTOS (Corrección de valores según tus últimas peticiones)
productos = {
    "BOLSA PAPEL CAFE #5 PQ/100": 0.832, "BOLSA PAPEL CAFE #6 PQ/100": 0.870,
    "BOLSA PAPEL CAFE #14 PQ/100": 1.364, "BOLSA PAPEL CAFE #20 PQ/100": 1.616,
    "CAJA TUTIS PZA": 0.048, "CAPACILLO CHINO PZA": 0.00104, "CAPACILLO ROJO #72 PZA": 0.000436,
    "CONT BISAG P/5-6 TUTIS PZA": 0.014, "CUCHARA MED DESCH PZA": 0.00165,
    "ETIQUETA CHAMPLITTE CHICA 4X4": 0.000328, "ETIQUETA CHAMPLITTE MED 6X6": 0.00057,
    "EMPLAYE GRANDE ROLLO": 1.174, "PAPEL ALUMINIO PZA": 1.342, "SERVILLETA PQ/500": 0.001192,
    "COFIA PQ/100": 0.238, "GUANTES TRANSP POLIURETANO PQ/100": 0.086,
    "HIGIENICO SCOTT ROLLO": 0.500, "TOALLA ROLLO 180M": 1.115, "BOLSA LOCK PZA": 0.018,
    "CAJA DE GRAPAS": 0.176, "CINTA TRANSP EMPAQUE": 0.272, "CINTA DELIMITADORA": 0.346,
    "COMPROBANTE TRASLADO VALORES": 0.0086, "ETIQUETA BLANCA ADH 13X19 PQ": 0.050,
    "HOJAS BLANCAS PQ/500": 2.146, "TINTA EPSON 544 (CMYK)": 0.078, "AGUA CIEL 20 LT": 1.0,
    "AZUCAR REFINADA KG": 1.0, "BOLSA CAMISETA LOGO CH KG": 1.0, "BOLSA CAMISETA LOGO GDE KG": 1.0,
    "BOLSA NATURAL 18X25 KG": 1.0, "PAPEL ENVOLTURA CHAMPLITTE KG": 1.0,
    "ROLLO POLIPUNTEADO 25X35 KG": 1.0, "BOLSA 90X120 KG": 1.0, "BOLSA 60X90 KG": 1.0,
    "CLOROLIMP L": 1.0, "FIBRA PREGON P/BAÑO": 1.0, "FIBRA SCOTCH BRITE": 1.0,
    "FIBRA AZUL P/CHAROLAS": 1.0, "JABON LIQUIDO MANOS L": 1.0, "LAVALOZA L": 1.0,
    "PRO GEL L": 1.0, "ROLLO TERMICO TPV": 1.0, "CUBETA PZA": 1.0, "ESCOBA PZA": 1.0,
    "ESCURRIDOR PZA": 1.0, "RECOGEDOR PZA": 1.0, "MECHUDO PZA": 1.0,
}

# CONFIGURACIÓN BARRA LATERAL
with st.sidebar:
    st.image("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR_M6u-Ksh98Xp_RSTj0YitG1L-0aO20WlY8w&s", width=100)
    st.markdown("### ⚙️ Configuración")
    numero_wa = st.selectbox("📱 WhatsApp Destino", ["522283530069", "522281111111"])
    
    with st.expander("🚨 Zona de Peligro"):
        confirmar = st.checkbox("Confirmar reset")
        if st.button("EJECUTAR RESET TOTAL"):
            if confirmar:
                c.execute("DELETE FROM pesajes_individuales")
                c.execute("DELETE FROM auditoria_stock")
                conn.commit()
                st.rerun()

# 4. INTERFAZ PRINCIPAL
tab_calc, tab_historial = st.tabs(["🧮 Nueva Entrada", "📋 Auditoría"])

with tab_calc:
    st.title("⚖️ Registro de Pesaje")
    
    # Reconocimiento de voz (simplificado)
    audio_bytes = st.audio_input("Grabar audio para dictado")
    texto_dictado = ""
    if audio_bytes:
        r = sr.Recognizer()
        with sr.AudioFile(audio_bytes) as source:
            audio = r.record(source)
            try:
                texto_dictado = r.recognize_google(audio, language="es-MX").upper()
                st.success(f"Escuchado: {texto_dictado}")
            except: st.error("No se entendió el audio")

    # Lógica de detección automática
    idx_sugerido = 0
    pue_sugerido = 1.0
    opciones = sorted(productos.keys())
    
    # Toggle de modo
    col_m1, col_m2 = st.columns(2)
    nuevo_art = col_m1.toggle("Artículo no listado")
    modo_preconteo = col_m2.toggle("Conteo manual (piezas)")

    if not nuevo_art:
        art_sel = st.selectbox("Producto:", opciones, index=idx_sugerido)
        pue_final = productos.get(art_sel, 1.0)
    else:
        art_sel = st.text_input("Nombre del producto:")
        pue_final = st.number_input("PUE Manual:", value=1.0, format="%.4f")

    with st.form("registro"):
        if modo_preconteo:
            cantidad = st.number_input("Piezas directas:", min_value=0.0)
            pb, tara, formula = 0.0, 0.0, "MANUAL"
        else:
            pb = st.number_input("Peso Bruto (kg):", format="%.3f")
            c1, c2, c3 = st.columns(3)
            # Pesos de tara actualizados según tu instrucción: contenedor .016, bisagra .045
            t_cont = c1.checkbox("Contenedor (0.016)")
            t_bis = c2.checkbox("Bisagra (0.045)")
            t_extra = c3.number_input("Extra:", value=0.0, format="%.3f")
            
            tara = (0.016 if t_cont else 0) + (0.045 if t_bis else 0) + t_extra
            offset = 0.030 if "TINTA" in art_sel.upper() else 0.0
            
            if pue_final > 0:
                calc = (pb - tara - offset) / pue_final
                cantidad = truncar_dos_decimales(calc)
                formula = f"({pb}-{tara}{'-0.03' if offset else ''})/{pue_final}"
            else:
                cantidad = 0
                formula = "Error PUE"

        if st.form_submit_button("GUARDAR"):
            if art_sel:
                fecha = datetime.now(pytz.timezone('America/Mexico_City')).strftime("%Y-%m-%d %H:%M")
                c.execute("INSERT INTO pesajes_individuales (fecha_hora, articulo, peso_bruto, tara, pue, resultado_pue, detalle_formula) VALUES (?,?,?,?,?,?,?)",
                          (fecha, art_sel, pb, tara, pue_final, cantidad, formula))
                conn.commit()
                st.success("Guardado")
                st.rerun()

with tab_historial:
    df = pd.read_sql("SELECT * FROM pesajes_individuales", conn)
    if not df.empty:
        # Buscador por texto
        busqueda = st.text_input("🔍 Filtrar historial:")
        if busqueda:
            df = df[df['articulo'].str.contains(busqueda.upper())]
        
        st.dataframe(df, use_container_width=True)
        
        # Exportación
        col1, col2 = st.columns(2)
        if col1.button("Generar Word"):
            st.download_button("Descargar Word", generar_word_tarjetas(df), "Tarjetas.docx")
            
        # WhatsApp link generator
        if not df.empty:
            total = df['resultado_pue'].sum()
            msg = f"Reporte: {df.iloc[-1]['articulo']} - Total: {total}"
            url = f"https://wa.me/{numero_wa}?text={urllib.parse.quote(msg)}"
            st.markdown(f'[📲 Enviar Reporte WhatsApp]({url})')
    else:
        st.info("No hay datos registrados.")

# Script para teclado móvil
components.html("<script>Array.from(window.parent.document.querySelectorAll('input')).forEach(i => i.setAttribute('enterkeyhint', 'done'))</script>", height=0)
