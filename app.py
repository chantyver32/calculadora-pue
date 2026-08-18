import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime, timedelta
import pytz
import math
import urllib.parse
import io
import base64
from fpdf import FPDF
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import re  
import os
import streamlit.components.v1 as components
import PyPDF2

# ------------------ 1. CONFIGURACIÓN GENERAL ------------------
st.set_page_config(page_title="Insumos Champlitte", page_icon="⚖️", layout="wide")

with st.spinner('Iniciando sistema Champlitte... 🥐'):
    zona_mx = pytz.timezone('America/Mexico_City')
    fecha_hoy_mx = datetime.now(zona_mx).date()

st.markdown("""
    <style>
    .block-container { padding-top: 3rem; padding-bottom: 1rem; }
    .main { background-color: #f5f7f9; }
    
    .stButton > button, 
    .stFormSubmitButton > button { 
        width: 100%; border-radius: 8px; font-weight: bold; 
        transition: none !important; -webkit-transition: none !important;
    }
    .stButton > button:focus, .stButton > button:active,
    .stFormSubmitButton > button:focus, .stFormSubmitButton > button:active {
        box-shadow: none !important; outline: none !important; transform: none !important;
    }

    [data-testid="stElementContainer"], [data-testid="stForm"] {
        transition: none !important; animation: none !important;
    }

    /* CENTRADO DEL MENSAJE DE CONFIRMACIÓN (TOAST) */
    div[data-testid="stToastContainer"] {
        top: 2rem !important; 
        bottom: auto !important; 
        left: 50% !important; 
        right: auto !important; 
        transform: translateX(-50%) !important;
        justify-content: center !important;
        align-items: center !important;
    }
    
    ul[role="listbox"] li[aria-selected="true"] {
        background-color: transparent !important; font-weight: bold !important;
    }

    div[data-baseweb="popover"] > div {
        background-color: #1a1a1c !important; border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important; box-shadow: 0 4px 12px rgba(0,0,0,0.8) !important;
    }
    div[data-baseweb="popover"] ul { background-color: transparent !important; }
    div[data-baseweb="popover"] li {
        background-color: transparent !important; color: #FFFFFF !important; font-size: 14px !important; padding: 10px 0 !important;
    }
    div[data-baseweb="popover"] li:hover { background-color: #2d2d30 !important; }
    div[data-baseweb="popover"] li[aria-selected="true"] { background-color: #3a3b3e !important; font-weight: bold !important; }

    div[data-baseweb="select"] > div {
        background-color: #1a1a1c !important; border-radius: 8px !important; border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }
    div[data-baseweb="select"] > div:focus-within { border-color: #ff4b4b !important; box-shadow: 0 0 0 1px #ff4b4b !important; }
    div[data-baseweb="select"] div, div[data-baseweb="select"] svg { color: #FFFFFF !important; fill: #FFFFFF !important; }

    .btn-wa {
        background-color: #25D366; color: white !important; padding: 10px 20px;
        text-align: center; text-decoration: none !important; display: block;
        font-size: 14px; font-weight: bold; border-radius: 8px; margin: 10px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .btn-wa:hover { background-color: #128C7E; }
    
    div[data-testid="stMetricValue"] { font-size: 28px; color: #1f77b4; }
    div[data-testid="stMetricDelta"] { font-size: 30px !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

if "show_toast" in st.session_state:
    st.toast(st.session_state.show_toast)
    del st.session_state.show_toast

# ------------------ 2. CONEXIÓN A SUPABASE Y ORDENAMIENTO OFICIAL ------------------
db_url = os.environ.get("SUPABASE_URL")
if not db_url:
    try:
        db_url = st.secrets["SUPABASE_URL"]
    except (FileNotFoundError, KeyError):
        st.error("🚨 Error crítico: No se encontró 'SUPABASE_URL'.")
        st.stop() 

conn = st.connection("supabase", type="sql", url=db_url)

ORDEN_CATEGORIAS_OFICIAL = ["Papelería Venta", "Limpieza Venta", "Insumos Venta"]

with conn.session as s:
    s.execute(text('''CREATE TABLE IF NOT EXISTS pesajes_individuales 
                 (id SERIAL PRIMARY KEY, sucursal TEXT, fecha_hora TEXT, articulo TEXT, categoria TEXT, 
                 peso_bruto REAL, tara REAL, pue REAL, resultado_pue REAL, detalle_formula TEXT)'''))

    s.execute(text('''CREATE TABLE IF NOT EXISTS pesajes_guardados 
                 (id SERIAL PRIMARY KEY, sucursal TEXT, fecha_hora TEXT, articulo TEXT, categoria TEXT, 
                 peso_bruto REAL, tara REAL, pue REAL, resultado_pue REAL, detalle_formula TEXT)'''))

    s.execute(text('''CREATE TABLE IF NOT EXISTS auditoria_stock 
                 (id SERIAL PRIMARY KEY, sucursal TEXT, articulo TEXT, categoria TEXT, 
                 total_real REAL, stock REAL, diferencia REAL, UNIQUE(sucursal, articulo))'''))
    
    s.execute(text('''CREATE TABLE IF NOT EXISTS usuarios 
                 (id SERIAL PRIMARY KEY, username TEXT, password TEXT)'''))
                 
    s.execute(text('''CREATE TABLE IF NOT EXISTS catalogo_productos 
                 (id SERIAL PRIMARY KEY, categoria TEXT, articulo TEXT, pue REAL, UNIQUE(categoria, articulo))'''))

    s.execute(text('ALTER TABLE pesajes_individuales ADD COLUMN IF NOT EXISTS categoria TEXT;'))
    s.execute(text('ALTER TABLE pesajes_guardados ADD COLUMN IF NOT EXISTS categoria TEXT;'))
    s.execute(text('ALTER TABLE auditoria_stock ADD COLUMN IF NOT EXISTS categoria TEXT;'))
    s.execute(text('ALTER TABLE pesajes_guardados ADD COLUMN IF NOT EXISTS aplicado_en_corte BOOLEAN DEFAULT TRUE;'))
    s.execute(text('ALTER TABLE catalogo_productos ADD COLUMN IF NOT EXISTS ubicacion_conteo TEXT DEFAULT \'Combinado\';'))
    s.execute(text('ALTER TABLE catalogo_productos ADD COLUMN IF NOT EXISTS redondeo TEXT DEFAULT \'No\';'))

    s.commit()

# ------------------ DICCIONARIO BASE ------------------
dicc_inicial = {
    "Insumos Venta": {
        "BOLSA PAPEL CAFE #5 POR PQ/100 PZAS A": 0.832, "BOLSA PAPEL CAFE #6 POR PQ/100 PZAS A": 0.870,
        "BOLSA PAPEL CAFE #14 POR PQ/100 PZAS M": 1.364, "BOLSA PAPEL CAFE #20 POR PQ/100 PZAS M": 1.616,
        "CAJA TUTIS POR PZA A": 0.048, "CAPACILLO CHINO POR PZA B": 0.00104, "CAPACILLO BLANCO POR PZA A": 0.000436,
        "CONT BISAG P/5-6 TUTIS POR PZA A": 0.014, "CUCHARA MED DESCH POR PZA A": 0.00165,
        "EMPLAYE GRANDE ROLLO POR PZA T": 1.174, "PAPEL ALUMINIO POR PZA T": 1.342, "SERVILLETA PQ/500 HJ POR PZA A": 0.001192,
        "BOLSA LOCK POR PZA A": 0.018,
        "AZUCAR REFINADA POR KG A": 1.0, "BOLSA CAMISETA LOGO CH POR KG A": 1.0, 
        "BOLSA CAMISETA LOGO GDE POR KG A": 1.0, "BOLSA NATURAL 18 X 25 POR KG A": 1.0, 
        "PAPEL ENVOLTURA CHAMPLITTE POR KG M": 1.0, "ROLLO POLIPUNTEADO 25 X 35 POR KG B": 1.0, 
        "BOLSA 90 X 120 POR KG A": 1.0, "BOLSA 60 X 90 POR KG M": 1.0
    },
    "Limpieza Venta": {
        "COFIA POR PQ/100 PZAS A": 0.238, "GUANTES TRANSP POLIURETANO POR PQ/100 PZAS A": 0.086,
        "FIBRA PREGON P/BAÑO POR PZA M": 1.0, "FIBRA SCOTCH BRITE POR PZA A": 1.0,
        "FIBRA AZUL P/LAVAR CHAROLAS POR PZA B": 1.0, "CUBETA POR PZA M": 1.0, "ESCOBA POR PZA A": 1.0, 
        "ESCURRIDOR POR PZA M": 1.0, "RECOGEDOR POR PZA M": 1.0, "MECHUDO POR PZA A": 1.0
    },
    "Papelería Venta": {
        "ETIQUETA CHAMPLITTE CHICA 4 X 4 POR PZA B": 0.000328, "ETIQUETA CHAMPLITTE MEDIANA 6 X 6 POR PZA B": 0.00057,
        "GRAPAS CJ POR PZA M": 0.164, "CINTA TRANSP EMPAQUE POR PZA M": 0.272, "CINTA DELIMITADORA POR PZA B": 0.346,
        "COMPROBANTE TRASLADO VALORES POR PZA A": 0.0086, "ETIQUETA BLANCA ADH 13 X 19 POR PQ M": 0.050,
        "HOJAS BLANCAS PQ/500 POR PZA A": 2.146, "TINTA EPSON 544 (CMYK) POR PZA A": 0.078, 
        "ROLLO TERMICO P/TPV POR PZA A": 1.0
    }
}

df_cat_global = conn.query("SELECT * FROM catalogo_productos", ttl="1h")
if df_cat_global.empty:
    with conn.session as s:
        for cat, prods in dicc_inicial.items():
            for art, pue in prods.items():
                s.execute(text("INSERT INTO catalogo_productos (categoria, articulo, pue, ubicacion_conteo, redondeo) VALUES (:c, :a, :p, 'Combinado', 'No') ON CONFLICT DO NOTHING"), 
                          {"c": cat, "a": art, "p": pue})
        s.commit()
    st.cache_data.clear() 
    df_cat_global = conn.query("SELECT * FROM catalogo_productos", ttl="1h")

productos_por_categoria = {}
for _, row in df_cat_global.iterrows():
    c = row['categoria']
    if c not in productos_por_categoria:
        productos_por_categoria[c] = {}
    productos_por_categoria[c][row['articulo']] = row['pue']

for c in ORDEN_CATEGORIAS_OFICIAL:
    if c not in productos_por_categoria:
        productos_por_categoria[c] = {}

# ------------------ SISTEMA DE LOGIN ------------------
def verificar_login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        st.markdown("<h2 style='text-align: center;'>⚖️ Baja de insumos</h2>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: gray; margin-bottom: 2rem;'>Control de Acceso</h4>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("form_login"):
                usuario_input = st.text_input("👤 Usuario:")
                password_input = st.text_input("🔑 Contraseña:", type="password")
                st.write("")
                btn_login = st.form_submit_button("Iniciar Sesión", use_container_width=True, type="primary")
                
                if btn_login:
                    df_check = conn.query("SELECT * FROM usuarios WHERE username = :u AND password = :p", 
                                          params={"u": usuario_input.strip(), "p": password_input}, ttl="10m")
                    if not df_check.empty:
                        st.session_state.autenticado = True
                        st.session_state.usuario_actual = usuario_input.strip()
                        st.session_state.show_toast = "✅ ¡Bienvenid@!"
                        st.rerun()
                    else:
                        st.error("❌ Usuario o contraseña incorrectos.")
        return False
    return True

if not verificar_login():
    st.stop()

# ------------------ BARRA LATERAL ------------------
with st.sidebar:
    st.markdown("### 🏢 Datos de Sesión")
    st.caption(f"👤 Conectado como: **{st.session_state.get('usuario_actual', 'Usuario')}**")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()
    st.divider()
    
    datos_sucursales = {
        "URANO": "522281342454", "COSTA DE ORO": "522292780850", "COSTA VERDE": "522299359597",
        "DÍAZ MIRÓN": "522291302759", "EJÉRCITO MEXICANO": "522299272107", "PLAZA RÍO": "522299864120",
        "PLAYAS DEL CONCHAL": "522291794020", "COYOL": "522299398334", "LA PLACITA": "522299208481",
        "CUAUHTÉMOC": "522291651340", "MARIO MOLINA": "522291780851", "RAFAEL CUERVO": "522291980229",
        "RÍO MEDIO": "522291005852", "DIVERPLAZA": "522293763180", "BOLÍVAR": "522291002947",
        "CIRCUNVALACIÓN": "522299393726", "J.B. LOBOS": "522299201956", "YÁÑEZ": "522293764940",
        "PALACIO DE HIERRO": "522299272100", "CIUDAD INDUSTRIAL": "522299200278", "DONATO CASAS": "522291653833",
        "LAS VEGAS": "522291932980", "PUENTE MORENO": "522296893999", "CONDESA": "522299863464",
        "MURILLO VIDAL": "522286886443", "ARAUCARIAS": "522281177133", "ÁVILA CAMACHO": "522288170989",
        "EMILIANO ZAPATA": "522969628525"
    }
    
    sucursal_in = st.selectbox("📍 Selecciona tu sucursal:", list(datos_sucursales.keys()))
    numero_wa = datos_sucursales[sucursal_in]
    st.caption(f"📱WhatsApp: **{numero_wa}**")

    st.divider()
    st.markdown("### 💾 Respaldo de Base de Datos")
    
    with st.form("form_restaurar_boveda"):
        uploaded_csv = st.file_uploader("⬆️ Subir Respaldo CSV", type=["csv"])
        btn_restaurar = st.form_submit_button("🔄 Restaurar Preconteos", use_container_width=True)
        if btn_restaurar:
            if uploaded_csv is not None:
                try:
                    df_upload = pd.read_csv(uploaded_csv)
                    if 'id' in df_upload.columns: df_upload = df_upload.drop(columns=['id'])
                    df_upload['sucursal'] = sucursal_in 
                    df_upload.to_sql("pesajes_guardados", con=conn.engine, if_exists="append", index=False)
                    st.session_state.show_toast = "✅ Respaldo restaurado con éxito"
                    st.rerun()
                except Exception as e: st.error(f"Error al restaurar: {e}")
            else: st.warning("⚠️ Primero selecciona un archivo CSV.")

    st.divider()
    if st.session_state.get('usuario_actual') == 'admin':
        with st.expander("🚨 Zona de Peligro (Formatear Nube)", expanded=False):
            confirmar_borrado = st.checkbox("Confirmar el formateo total")
            if st.button("⚠️ ELIMINAR TODO.", use_container_width=True):
                if not confirmar_borrado: st.error("Debes confirmar primero")
                else:
                    with conn.session as s:
                        s.execute(text("DROP TABLE IF EXISTS pesajes_individuales, pesajes_guardados, auditoria_stock CASCADE"))
                        s.commit()
                    st.session_state.show_toast = "✅ Base de datos eliminada"
                    st.rerun()

# ------------------ FUNCIONES AUXILIARES ------------------
def truncar_dos_decimales(valor):
    if valor is None: return 0.0
    s = f"{float(valor):.10f}"
    entero, decimal = s.split('.')
    return float(f"{entero}.{decimal[:2]}")

def formato_estricto(valor):
    if pd.isna(valor) or valor is None: return "0.00"
    s = f"{float(valor):.10f}" 
    entero, decimal = s.split('.')
    return f"{entero}.{decimal[:2]}"

@st.dialog("✅ Registrado", width="large")
def mostrar_popup_exito():
    datos = st.session_state.item_a_guardar
    articulo = datos["articulo"]
    resultado = datos["resultado"]
    sucursal = datos["sucursal"]
    categoria = datos["categoria"]
    peso_bruto = datos["peso_bruto"]
    tara = datos["tara"]
    pue = datos["pue"]
    formula = datos["formula"]
    nuevo_art = datos["nuevo_art"]
    modo_preconteo = datos["modo_preconteo"]
    fecha_mexico = datos["fecha_mexico"]
    num_opciones = datos["num_opciones"]

    st.markdown(f"### 📦 {articulo}")
    
    df_actual_art = conn.query("SELECT * FROM pesajes_individuales WHERE articulo = :art AND sucursal = :suc", params={"art": articulo, "suc": sucursal}, ttl=0)
    df_guardados_art = conn.query("SELECT * FROM pesajes_guardados WHERE articulo = :art AND sucursal = :suc AND (aplicado_en_corte = FALSE OR aplicado_en_corte IS NULL)", params={"art": articulo, "suc": sucursal}, ttl=0)
    df_art_combined = pd.concat([df_actual_art, df_guardados_art], ignore_index=True)
    
    sum_anterior = truncar_dos_decimales(df_art_combined['resultado_pue'].sum())
    total_real = truncar_dos_decimales(sum_anterior + resultado)
    
    sumandos = [formato_estricto(val) for val in df_art_combined['resultado_pue']]
    sumandos.append(formato_estricto(resultado))
    texto_total = f"{' + '.join(sumandos)} = {formato_estricto(total_real)}" if len(sumandos) > 1 else formato_estricto(total_real)
    
    st.metric("TOTAL CALCULADO (Sesión + Bóveda)", texto_total)
    st.divider()
    
    df_stock = conn.query("SELECT stock FROM auditoria_stock WHERE articulo = :art AND sucursal = :suc", params={"art": articulo, "suc": sucursal}, ttl=0)
    saved_stock = float(df_stock.iloc[0]['stock']) if not df_stock.empty else None
    
    diferencia_valida = True
    col_st1, col_st2 = st.columns(2)
    with col_st1:
        stock_teorico = st.number_input("Valor en Sistema (Stock):", value=saved_stock, placeholder="Ingresa y presiona Enter", key=f"modal_stock_{articulo}")
        
    with col_st2:
        if stock_teorico is not None:
            diferencia = truncar_dos_decimales(total_real - stock_teorico)
            st.metric("DIFERENCIA", value=" ", delta=formato_estricto(diferencia), delta_color="inverse")
            
            if diferencia > 0:
                diferencia_valida = False
                st.error("⚠️ Diferencia en rojo. El pesaje será omitido (no se guardará).")
    
    st.divider()
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    def avanzar_y_cerrar():
        if not nuevo_art:
            if st.session_state.auto_index < num_opciones - 1:
                st.session_state.auto_index += 1
            else:
                st.session_state.pending_transition = True
        del st.session_state.item_a_guardar

    with col1:
        if st.button("Continuar", type="primary", use_container_width=True):
            if diferencia_valida:
                with conn.session as s:
                    s.execute(text("""INSERT INTO pesajes_individuales 
                                 (sucursal, fecha_hora, articulo, categoria, peso_bruto, tara, pue, resultado_pue, detalle_formula) 
                                 VALUES (:suc, :fh, :art, :cat, :pb, :tara, :pue, :rp, :df)"""),
                              {"suc": sucursal, "fh": fecha_mexico, "art": articulo, "cat": categoria, 
                               "pb": peso_bruto if not modo_preconteo else 0.0, 
                               "tara": tara if not modo_preconteo else 0.0, 
                               "pue": pue if not modo_preconteo else 0.0, 
                               "rp": resultado, "df": formula})
                    if stock_teorico is not None:
                        s.execute(text("""INSERT INTO auditoria_stock (sucursal, articulo, categoria, total_real, stock, diferencia) 
                                     VALUES (:suc, :art, :cat, :tr, :stk, :dif)
                                     ON CONFLICT (sucursal, articulo) DO UPDATE 
                                     SET total_real = EXCLUDED.total_real, stock = EXCLUDED.stock, diferencia = EXCLUDED.diferencia, categoria = EXCLUDED.categoria"""), 
                                  {"suc": sucursal, "art": articulo, "cat": categoria, "tr": total_real, "stk": stock_teorico, "dif": diferencia})
                    s.commit()
            avanzar_y_cerrar()
            st.rerun() 
            
    with col2:
        if diferencia_valida:
            if st.button("📥 Enviar a Bóveda", type="secondary", use_container_width=True):
                with conn.session as s:
                    s.execute(text("""INSERT INTO pesajes_guardados 
                                 (sucursal, fecha_hora, articulo, categoria, peso_bruto, tara, pue, resultado_pue, detalle_formula, aplicado_en_corte) 
                                 VALUES (:suc, :fh, :art, :cat, :pb, :tara, :pue, :rp, :df, FALSE)"""),
                              {"suc": sucursal, "fh": fecha_mexico, "art": articulo, "cat": categoria, 
                               "pb": peso_bruto if not modo_preconteo else 0.0, 
                               "tara": tara if not modo_preconteo else 0.0, 
                               "pue": pue if not modo_preconteo else 0.0, 
                               "rp": resultado, "df": formula})
                    if stock_teorico is not None:
                        s.execute(text("""INSERT INTO auditoria_stock (sucursal, articulo, categoria, total_real, stock, diferencia) 
                                     VALUES (:suc, :art, :cat, :tr, :stk, :dif)
                                     ON CONFLICT (sucursal, articulo) DO UPDATE 
                                     SET total_real = EXCLUDED.total_real, stock = EXCLUDED.stock, diferencia = EXCLUDED.diferencia, categoria = EXCLUDED.categoria"""), 
                                  {"suc": sucursal, "art": articulo, "cat": categoria, "tr": total_real, "stk": stock_teorico, "dif": diferencia})
                    s.commit()
                avanzar_y_cerrar()
                st.session_state.show_toast = "✅ Trasladado a la Bóveda."
                st.rerun()

    with col3:
        if st.button("❌ Cancelar", type="secondary", use_container_width=True):
            del st.session_state.item_a_guardar
            st.rerun()

@st.dialog("⏭️ Confirmar Avance")
def dialog_confirmar_transicion(orden_categorias, orden_ubicaciones, sucursal):
    idx_cat = st.session_state.cat_idx
    idx_ubi = st.session_state.ubi_idx
    
    next_cat_idx = idx_cat
    next_ubi_idx = idx_ubi
    is_complete = False

    if idx_cat < len(orden_categorias) - 1:
        next_cat_idx = idx_cat + 1
    else:
        next_cat_idx = 0
        if idx_ubi < len(orden_ubicaciones) - 1:
            next_ubi_idx = idx_ubi + 1
        else:
            is_complete = True

    if is_complete:
        st.success("🎉 ¡Has completado todas las categorías en todas las ubicaciones!")
        
        if st.button("🔄 Finalizar y Volver al inicio", type="primary", use_container_width=True):
            st.session_state.pending_transition = False
            st.session_state.cat_idx = 0
            st.session_state.ubi_idx = 0
            st.session_state.auto_index = 0
            st.rerun()

    else:
        st.write(f"Terminaste con todos los productos de **{orden_categorias[idx_cat]}**.")
        st.info(f"¿Deseas pasar a **{orden_categorias[next_cat_idx]}** en **{orden_ubicaciones[next_ubi_idx]}**?")
        
        if st.button("✅ Sí, avanzar", type="primary", use_container_width=True):
            st.session_state.cat_idx = next_cat_idx
            st.session_state.ubi_idx = next_ubi_idx
            st.session_state.auto_index = 0
            st.session_state.pending_transition = False
            st.rerun()

        if st.button("❌ No, quedarme aquí", use_container_width=True):
            st.session_state.pending_transition = False
            st.rerun()

def generar_word_tarjetas(df):
    doc = Document()
    for section in doc.sections:
        section.page_width, section.page_height = Cm(21.59), Cm(27.94)
        section.top_margin = section.bottom_margin = section.left_margin = section.right_margin = Cm(1.5)
        
    cols = 3
    rows = (len(df) + cols - 1) // cols or 1
    table = doc.add_table(rows=rows, cols=cols)
    
    tblBorders = OxmlElement('w:tblBorders')
