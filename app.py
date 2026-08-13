import streamlit as st
import pandas as pd
from sqlalchemy import text
from datetime import datetime, timedelta
import pytz
import urllib.parse
import io
import speech_recognition as sr
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import re  
import os
import gc
import streamlit.components.v1 as components

# --- OPTIMIZACIÓN DE MEMORIA (Debe ir antes de importar pyplot) ---
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

# ------------------ 1. CONFIGURACIÓN GENERAL ------------------
st.set_page_config(page_title="Insumos Champlitte", page_icon="⚖️", layout="wide")

with st.spinner('Iniciando sistema Champlitte... 🥐'):
    zona_mx = pytz.timezone('America/Mexico_City')
    fecha_hoy_mx = datetime.now(zona_mx).date()

st.markdown("""
    <style>
    .block-container { padding-top: 3rem; padding-bottom: 1rem; }
    
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

    div[data-testid="stToastContainer"] {
        top: 2rem !important; bottom: auto !important; right: 2rem !important;
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
    /* CAMBIO A BLANCO EN EL BORDE DE FOCO */
    div[data-baseweb="select"] > div:focus-within { border-color: #FFFFFF !important; box-shadow: 0 0 0 1px #FFFFFF !important; }
    div[data-baseweb="select"] div, div[data-baseweb="select"] svg { color: #FFFFFF !important; fill: #FFFFFF !important; }

    .btn-wa {
        background-color: #25D366; color: white !important; padding: 10px 20px;
        text-align: center; text-decoration: none !important; display: block;
        font-size: 14px; font-weight: bold; border-radius: 8px; margin: 10px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .btn-wa:hover { background-color: #128C7E; }
    
    /* CAMBIO A BLANCO EN LAS MÉTRICAS */
    div[data-testid="stMetricValue"] { font-size: 28px; color: #FFFFFF; }
    div[data-testid="stMetricDelta"] { font-size: 30px !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

if "show_toast" in st.session_state:
    st.toast(st.session_state.show_toast)
    del st.session_state.show_toast
if "show_success" in st.session_state:
    st.success(st.session_state.show_success)
    del st.session_state.show_success
if "show_error" in st.session_state:
    st.error(st.session_state.show_error)
    del st.session_state.show_error

# ------------------ 2. CONEXIÓN A SUPABASE ------------------
db_url = os.environ.get("SUPABASE_URL")
if not db_url:
    try:
        db_url = st.secrets["SUPABASE_URL"]
    except (FileNotFoundError, KeyError):
        st.error("🚨 Error crítico: No se encontró 'SUPABASE_URL'.")
        st.stop() 

conn = st.connection("supabase", type="sql", url=db_url)

with conn.session as s:
    # 1. Creación de tablas base (si no existen)
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

    # 2. PARCHE: Agrega la columna "categoria" si las tablas ya existían antes
    s.execute(text('ALTER TABLE pesajes_individuales ADD COLUMN IF NOT EXISTS categoria TEXT;'))
    s.execute(text('ALTER TABLE pesajes_guardados ADD COLUMN IF NOT EXISTS categoria TEXT;'))
    s.execute(text('ALTER TABLE auditoria_stock ADD COLUMN IF NOT EXISTS categoria TEXT;'))

    s.commit()

# ------------------ SISTEMA DE LOGIN ------------------
def verificar_login():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False

    if not st.session_state.autenticado:
        # CAMBIO A BLANCO EN EL TÍTULO
        st.markdown("<h2 style='text-align: center; color: #FFFFFF;'>⚖️ Champlitte Insumos</h2>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: gray; margin-bottom: 2rem;'>Control de Acceso</h4>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("form_login"):
                usuario_input = st.text_input("👤 Usuario:")
                password_input = st.text_input("🔑 Contraseña:", type="password")
                btn_login = st.form_submit_button("Iniciar Sesión", use_container_width=True, type="primary")
                
                if btn_login:
                    df_check = conn.query("SELECT * FROM usuarios WHERE username = :u AND password = :p", 
                                          params={"u": usuario_input.strip(), "p": password_input}, ttl=0)
                    if not df_check.empty:
                        st.session_state.autenticado = True
                        st.session_state.usuario_actual = usuario_input.strip()
                        st.session_state.show_toast = "✅ ¡Bienvenid@!"
                        st.rerun()
                    else:
                        if usuario_input == "admin" and password_input == "admin":
                             st.session_state.autenticado = True
                             st.session_state.usuario_actual = "admin"
                             st.rerun()
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
    st.markdown("### 💾 Respaldo Bóveda")
    with st.form("form_restaurar_boveda"):
        uploaded_csv = st.file_uploader("⬆️ Subir Respaldo CSV", type=["csv"])
        btn_restaurar = st.form_submit_button("🔄 Restaurar Preconteos")
        if btn_restaurar and uploaded_csv is not None:
            try:
                df_upload = pd.read_csv(uploaded_csv)
                if 'id' in df_upload.columns: df_upload = df_upload.drop(columns=['id'])
                df_upload['sucursal'] = sucursal_in 
                df_upload.to_sql("pesajes_guardados", con=conn.engine, if_exists="append", index=False)
                st.session_state.show_toast = "✅ Respaldo restaurado con éxito"
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

    if st.session_state.get('usuario_actual') == 'admin':
        st.divider()
        with st.expander("🚨 Zona de Peligro", expanded=False):
            st.warning("⚠️ ESTE BOTÓN BORRA TODA LA BASE DE DATOS.")
            confirmar_borrado = st.checkbox("Confirmar formateo")
            if st.button("⚠️ ELIMINAR TODO"):
                if confirmar_borrado:
                    with conn.session as s:
                        s.execute(text("DROP TABLE IF EXISTS pesajes_individuales, pesajes_guardados, auditoria_stock CASCADE"))
                        s.commit()
                    st.session_state.show_toast = "✅ DB Formateada"
                    st.rerun()

# ------------------ DICCIONARIO CATEGORIZADO (UNIFICADO) ------------------
productos_por_categoria = {
    "Insumos Venta": {
        "BOLSA PAPEL CAFE #5 POR PQ/100 PZAS A": 0.832, "BOLSA PAPEL CAFE #6 POR PQ/100 PZAS A": 0.870,
        "BOLSA PAPEL CAFE #14 POR PQ/100 PZAS M": 1.364, "BOLSA PAPEL CAFE #20 POR PQ/100 PZAS M": 1.616,
        "CAJA TUTIS POR PZA A": 0.048, "CAPACILLO CHINO POR PZA B": 0.00104, "CAPACILLO BLANCO POR PZA A": 0.000436,
        "CONT BISAG P/5-6 TUTIS POR PZA A": 0.014, "CUCHARA MED DESCH POR PZA A": 0.00165,
        "EMPLAYE GRANDE ROLLO POR PZA T": 1.174, "PAPEL ALUMINIO POR PZA T": 1.342, "SERVILLETA PQ/500 HJ POR PZA A": 0.001192,
        "COFIA POR PQ/100 PZAS A": 0.238, "GUANTES TRANSP POLIURETANO POR PQ/100 PZAS A": 0.086,
        "HIGIENICO SCOTT ROLLO POR PZA M": 0.500, "TOALLA ROLLO 180M POR PZA M": 1.115, "BOLSA LOCK POR PZA A": 0.018,
        "AGUA CIEL 20 POR LT A": 1.0, "AZUCAR REFINADA POR KG A": 1.0, "BOLSA CAMISETA LOGO CH POR KG A": 1.0, 
        "BOLSA CAMISETA LOGO GDE POR KG A": 1.0, "BOLSA NATURAL 18 X 25 POR KG A": 1.0, 
        "PAPEL ENVOLTURA CHAMPLITTE POR KG M": 1.0, "ROLLO POLIPUNTEADO 25 X 35 POR KG B": 1.0, 
        "BOLSA 90 X 120 POR KG A": 1.0, "BOLSA 60 X 90 POR KG M": 1.0
    },
    "Limpieza Venta": {
        "CLOROLIMP POR L A": 1.0, "FIBRA PREGON P/BAÑO POR PZA M": 1.0, "FIBRA SCOTCH BRITE POR PZA A": 1.0,
        "FIBRA AZUL P/LAVAR CHAROLAS POR PZA B": 1.0, "JABON LIQUIDO PARA MANOS POR L M": 1.0, "LAVALOZA POR L A": 1.0,
        "PRO GEL POR L B": 1.0, "CUBETA POR PZA M": 1.0, "ESCOBA POR PZA A": 1.0, "ESCURRIDOR POR PZA M": 1.0, 
        "RECOGEDOR POR PZA M": 1.0, "MECHUDO POR PZA A": 1.0
    },
    "Papelería Venta": {
        "ETIQUETA CHAMPLITTE CHICA 4 X 4 POR PZA B": 0.000328, "ETIQUETA CHAMPLITTE MEDIANA 6 X 6 POR PZA B": 0.00057,
        "GRAPAS CJ POR PZA M": 0.164, "CINTA TRANSP EMPAQUE POR PZA M": 0.272, "CINTA DELIMITADORA POR PZA B": 0.346,
        "COMPROBANTE TRASLADO VALORES POR PZA A": 0.0086, "ETIQUETA BLANCA ADH 13 X 19 POR PQ M": 0.050,
        "HOJAS BLANCAS PQ/500 POR PZA A": 2.146, "TINTA EPSON 544 (CMYK) POR PZA A": 0.078, 
        "ROLLO TERMICO P/TPV POR PZA A": 1.0
    }
}

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

@st.dialog("✅ Registrado")
def mostrar_popup_exito(id_registro, articulo, resultado_ultimo, sucursal, categoria):
    st.markdown(f"### 📦 {articulo}")
    df_actual_art = conn.query("SELECT * FROM pesajes_individuales WHERE articulo = :art AND sucursal = :suc", params={"art": articulo, "suc": sucursal}, ttl=0)
    df_guardados_art = conn.query("SELECT * FROM pesajes_guardados WHERE articulo = :art AND sucursal = :suc", params={"art": articulo, "suc": sucursal}, ttl=0)
    df_art_combined = pd.concat([df_actual_art, df_guardados_art], ignore_index=True)
    
    total_real = truncar_dos_decimales(df_art_combined['resultado_pue'].sum())
    sumandos = [formato_estricto(val) for val in df_art_combined['resultado_pue']]
    texto_total = f"{' + '.join(sumandos)} = {formato_estricto(total_real)}" if len(sumandos) > 1 else formato_estricto(total_real)
    st.metric("TOTAL CALCULADO", texto_total)
    
    st.divider()
    df_stock = conn.query("SELECT stock FROM auditoria_stock WHERE articulo = :art AND sucursal = :suc", params={"art": articulo, "suc": sucursal}, ttl=0)
    saved_stock = float(df_stock.iloc[0]['stock']) if not df_stock.empty else None
    
    col_st1, col_st2 = st.columns(2)
    with col_st1:
        stock_teorico = st.number_input("Valor en Sistema (Stock):", value=saved_stock, key=f"modal_stock_{id_registro}")
        
    with col_st2:
        if stock_teorico is not None:
            diferencia = truncar_dos_decimales(total_real - stock_teorico)
            st.metric("DIFERENCIA", value=" ", delta=formato_estricto(diferencia), delta_color="inverse")
            with conn.session as s:
                s.execute(text("""INSERT INTO auditoria_stock (sucursal, articulo, categoria, total_real, stock, diferencia) 
                             VALUES (:suc, :art, :cat, :tr, :stk, :dif)
                             ON CONFLICT (sucursal, articulo) DO UPDATE 
                             SET total_real = EXCLUDED.total_real, stock = EXCLUDED.stock, diferencia = EXCLUDED.diferencia"""), 
                          {"suc": sucursal, "art": articulo, "cat": categoria, "tr": total_real, "stk": stock_teorico, "dif": diferencia})
                s.commit()
    
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Continuar", type="primary", use_container_width=True): st.rerun()
    with col2:
        if st.button("📥 Enviar a Bóveda", type="secondary", use_container_width=True):
            with conn.session as s:
                s.execute(text("""INSERT INTO pesajes_guardados (sucursal, fecha_hora, articulo, categoria, peso_bruto, tara, pue, resultado_pue, detalle_formula)
                             SELECT sucursal, fecha_hora, articulo, categoria, peso_bruto, tara, pue, resultado_pue, detalle_formula 
                             FROM pesajes_individuales WHERE id = :id"""), {"id": id_registro})
                s.execute(text("DELETE FROM pesajes_individuales WHERE id = :id"), {"id": id_registro})
                s.commit()
            st.session_state.show_toast = "✅ Trasladado a la Bóveda."
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
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        border_el = OxmlElement(f'w:{edge}')
        border_el.set(qn('w:val'), 'dashed'); border_el.set(qn('w:sz'), '4'); border_el.set(qn('w:space'), '0'); border_el.set(qn('w:color'), '000000')
        tblBorders.append(border_el)
    table._tbl.tblPr.append(tblBorders)
    
    for idx, row_data in df.iterrows():
        cell = table.cell(idx // cols, idx % cols)
        cell.width = Cm(6)
        table.rows[idx // cols].height = Cm(4)
        table.rows[idx // cols].height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
        tcVAlign = OxmlElement('w:vAlign')
        tcVAlign.set(qn('w:val'), 'center')
        cell._tc.get_or_add_tcPr().append(tcVAlign)
        
        art, res = str(row_data['articulo']), formato_estricto(row_data['resultado_pue'])
        if "PZA" in art.upper() and res.endswith(".00"): res = res[:-3]
        
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run1 = p.add_run(f"{art}\n")
        run1.font.size, run1.bold = Pt(8), True
        run2 = p.add_run(f"\n{res}")
        run2.font.size, run2.bold = Pt(12), True
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def generar_imagen_esquema(df_stock, sucursal):
    fig_height = max(5.0, len(df_stock) * 0.45 + 3.5) 
    fig, ax = plt.subplots(figsize=(11, fig_height), dpi=200)
    ax.axis('off')
    
    # EL COLOR VINO SE MANTIENE AQUÍ ADENTRO
    champlitte_red, light_pink, text_dark = '#8A1538', '#FDF2F4', '#333333'      
    
    fig.text(0.5, 0.93, "Champlitte", fontsize=36, fontweight='bold', color=champlitte_red, ha='center', va='center', family='serif')
    fig.text(0.5, 0.89, "P A S T E L E R Í A", fontsize=10, fontweight='bold', color=text_dark, ha='center', va='center')
    fig.text(0.5, 0.85, "CONTROL GENERAL DE INVENTARIO", fontsize=18, fontweight='bold', color=champlitte_red, ha='center', va='center')
    
    fecha_actual = datetime.now(zona_mx).strftime('%d %m %Y - %H:%M')
    fig.text(0.5, 0.81, f"SUCURSAL: {sucursal} | {fecha_actual}", fontsize=9, fontweight='bold', color='#7f8c8d', ha='center', va='center')
    
    columns = ["PRODUCTO", "CATEGORÍA", "CANT. ANT.", "PESO OBT.", "STOCK ACT."]
    table_data = [[f"  {r['Producto']}", str(r['Categoría']), formato_estricto(r['Cantidad Anterior']), formato_estricto(r['Peso Obtenido']), formato_estricto(r['Stock Actual'])] for _, r in df_stock.iterrows()]
        
    table = ax.table(cellText=table_data, colLabels=columns, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2.0) 
    
    for key, cell in table.get_celld().items():
        cell.set_edgecolor('white'); cell.set_linewidth(2)
        if key[0] == 0: 
            cell.set_facecolor(champlitte_red); cell.set_text_props(color='white', fontweight='bold', fontsize=8.5)
            if key[1] == 0: cell.set_text_props(ha='left')
        else: 
            cell.set_facecolor('white' if key[0] % 2 == 1 else light_pink)
            if key[1] == 0: cell.set_text_props(color=text_dark, ha='left')
            elif key[1] == 4: cell.set_text_props(color=champlitte_red, fontweight='bold')
            else: cell.set_text_props(color=text_dark, fontweight='bold')
                
    plt.subplots_adjust(top=0.75, bottom=0.05) 
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor='white', pad_inches=0.4)
    buf.seek(0)
    
    # --- LIMPIEZA EXTREMA DE MEMORIA ---
    fig.clf()
    plt.close(fig)
    gc.collect()
    # -----------------------------------
    
    return buf

# ------------------ 3. INTERFAZ PRINCIPAL (4 TABS) ------------------
tab_stock, tab_calc, tab_historial, tab_visual = st.tabs(["📦 Stock Real", "🧮 Nueva Entrada & Auditoría", "📋 Reportes y Bóveda", "🖼️ Esquema Visual"])

# --- TAB 0: STOCK REAL POR CATEGORÍAS ---
with tab_stock:
    st.subheader("📦 Control de Stock Real e Inventario Dinámico")
    categoria_activa = st.selectbox("📂 Seleccione la Categoría de Inventario:", list(productos_por_categoria.keys()))
    productos_dict = productos_por_categoria[categoria_activa]

    df_actual_all = conn.query("SELECT articulo, SUM(resultado_pue) as total_pesado FROM pesajes_individuales WHERE sucursal = :suc AND categoria = :cat GROUP BY articulo", params={"suc": sucursal_in, "cat": categoria_activa}, ttl=0)
    df_total_pesado = df_actual_all.groupby("articulo", as_index=False)["total_pesado"].sum() if not df_actual_all.empty else df_actual_all.copy()
    df_auditoria_base = conn.query("SELECT articulo, stock FROM auditoria_stock WHERE sucursal = :suc AND categoria = :cat", params={"suc": sucursal_in, "cat": categoria_activa}, ttl=0)

    lista_todos_articulos = sorted(list(set(list(productos_dict.keys()) + list(df_auditoria_base['articulo'] if not df_auditoria_base.empty else []))))
    df_stock_master = pd.DataFrame({"articulo": lista_todos_articulos})
    df_stock_master = pd.merge(df_stock_master, df_auditoria_base, on="articulo", how="left") if not df_auditoria_base.empty else df_stock_master.assign(stock=0.0)
    df_stock_master = pd.merge(df_stock_master, df_total_pesado, on="articulo", how="left").fillna({"total_pesado": 0.0}) if not df_total_pesado.empty else df_stock_master.assign(total_pesado=0.0)

    df_stock_master["stock"] = df_stock_master["stock"].fillna(0.0)
    df_stock_master["cantidad_actual"] = df_stock_master["stock"] - df_stock_master["total_pesado"]
    df_stock_display = df_stock_master[["stock", "total_pesado", "articulo", "cantidad_actual"]].rename(columns={"stock": "Cantidad Anterior", "total_pesado": "Peso Descontado", "articulo": "Producto", "cantidad_actual": "Cantidad Actual"})

    df_editado = st.data_editor(df_stock_display, use_container_width=True, hide_index=True, disabled=["Peso Descontado", "Producto", "Cantidad Actual"], key=f"editor_stock_{categoria_activa}")

    if st.button(f"💾 Guardar Cambios ({categoria_activa})", use_container_width=True):
        with conn.session as s:
            for _, row in df_editado.iterrows():
                s.execute(text("""INSERT INTO auditoria_stock (sucursal, articulo, categoria, stock, total_real, diferencia) VALUES (:suc, :art, :cat, :stk, 0, 0)
                             ON CONFLICT (sucursal, articulo) DO UPDATE SET stock = EXCLUDED.stock"""), {"suc": sucursal_in, "art": row["Producto"], "cat": categoria_activa, "stk": row["Cantidad Anterior"]})
            s.commit()
        st.session_state.show_toast = f"✅ Stock inicial guardado para {categoria_activa}."
        st.rerun()

    st.divider()
    if st.button(f"🔄 CONVERTIR STOCK ACTUAL DE {categoria_activa.upper()} PARA MAÑANA", type="primary", use_container_width=True):
        with conn.session as s:
            for _, row in df_stock_master[df_stock_master["total_pesado"] > 0].iterrows():
                s.execute(text("""INSERT INTO auditoria_stock (sucursal, articulo, categoria, stock, total_real, diferencia) VALUES (:suc, :art, :cat, :stk, 0, 0)
                             ON CONFLICT (sucursal, articulo) DO UPDATE SET stock = EXCLUDED.stock"""), {"suc": sucursal_in, "art": row["articulo"], "cat": categoria_activa, "stk": row["cantidad_actual"]})
            s.execute(text("DELETE FROM pesajes_individuales WHERE sucursal = :suc AND categoria = :cat"), {"suc": sucursal_in, "cat": categoria_activa})
            s.commit()
        st.session_state.show_toast = f"✅ ¡Actualizado para mañana!"
        st.rerun()

# --- TAB 1: REGISTRO, AUDIO Y AUDITORÍA ---
with tab_calc:
    cat_reg = st.selectbox("📂 Seleccione Categoría de Registro:", list(productos_por_categoria.keys()), key="cat_reg")
    productos_dict_reg = productos_por_categoria[cat_reg]
    opciones = sorted(productos_dict_reg.keys())
    
    with st.expander("🎤 **Ingreso por Voz** (Click para desplegar)", expanded=False):
        audio_bytes = st.audio_input("Di algo como: 0.620 de capacillo chino en contenedor.", key="audio_reg")
        texto_filtro = ""
        if audio_bytes:
            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_bytes) as source:
                try:
                    texto_reconocido = recognizer.recognize_google(recognizer.record(source), language="es-MX")
                    st.toast(f"🎤 Escuchado: {texto_reconocido}")
                    components.html(f'<script>const u = new SpeechSynthesisUtterance("{texto_reconocido}"); u.lang="es-MX"; window.speechSynthesis.speak(u);</script>', height=0)
                    texto_filtro = texto_reconocido.upper()
                except Exception: st.error("Error al procesar el audio.")
    
    idx_sugerido, peso_sugerido, pue_sugerido, t_cont_sugerido, nombre_limpio = None, None, None, False, ""
    
    if texto_filtro:
        if "CONTENEDOR" in texto_filtro: t_cont_sugerido = True
        match_pue = re.search(r'(?:PESO UNITARIO|UNITARIO|PUE|ESTÁNDAR|ESTANDAR)[^\d]*(\d+(?:[.,]\d+)?)', texto_filtro)
        if match_pue: pue_sugerido = float(match_pue.group(1).replace(',', '.'))
        nums = [float(n.replace(',', '.')) for n in re.findall(r'\d+(?:[.,]\d+)?', texto_filtro)]
        if pue_sugerido in nums: nums.remove(pue_sugerido) 
        if nums: peso_sugerido = nums[0] 
        
        texto_limpio = texto_filtro
        for p in [r'\d+(?:[.,]\d+)?', 'PESO UNITARIO', 'PUE', 'PESO', 'UNITARIO', 'ESTÁNDAR', 'ESTANDAR', 'KILOS', 'KG', 'GRAMOS', 'CON', 'SIN', 'Y', 'DE', 'EL', 'LA', 'CONTENEDOR', 'BISAGRA', 'LLEVA', 'ASIGNAR']:
            texto_limpio = re.sub(r'\b' + p + r'\b', '', texto_limpio)
        nombre_limpio = ' '.join(texto_limpio.split()) 
        
        if nombre_limpio:
            max_c = 0
            for i, prod in enumerate(opciones):
                c = sum(1 for p in nombre_limpio.split() if p in prod.upper())
                if c > max_c: max_c, idx_sugerido = c, i

    modo_seleccionado = st.selectbox("⚙️ Modo de Registro:", ["Modo Normal", "Artículo NO listado", "PRE-CONTEO MANUAL (Piezas directas)"])
    nuevo_art, modo_preconteo = (modo_seleccionado == "Artículo NO listado"), (modo_seleccionado == "PRE-CONTEO MANUAL (Piezas directas)")
    
    if not nuevo_art:
        art_sel = st.selectbox("Seleccione Artículo:", opciones, index=idx_sugerido, placeholder="Elija...")
        pue_final = productos_dict_reg.get(art_sel, 1.0) if art_sel else 1.0
    else:
        c_n1, c_n2 = st.columns([2,1])
        with c_n1: art_sel = st.text_input("Nombre del Nuevo Artículo:", value=nombre_limpio if nombre_limpio else None)
        with c_n2: pue_final = st.number_input("Asignar Peso Unitario:", value=pue_sugerido, format="%.4f")

    with st.form(key="form_pesaje", clear_on_submit=True):
        if modo_preconteo:
            st.info("💡 En este modo se registra la cantidad directa sin cálculos de peso.")
            cantidad_directa = st.number_input("Cantidad de piezas:", value=peso_sugerido, step=1.0)
            peso_bruto = tara_total = 0.0; formula = "CONTEO MANUAL DIRECTO"
        else:
            peso_bruto = st.number_input("Peso Bruto de Báscula (kg):", value=peso_sugerido, format="%.3f")
            with st.expander("🛠️ Configuración de Taras", expanded=True):
                c1, c2 = st.columns(2)
                with c1: t_cont = st.checkbox("Contenedor (0.045)", value=t_cont_sugerido)
                with c2: t_manual = st.number_input("Tara Manual Extra:", value=None, format="%.3f")
        
        btn_save = st.form_submit_button("📥 CONFIRMAR Y GUARDAR REGISTRO")

    if btn_save:
        if art_sel and (cantidad_directa is not None if modo_preconteo else (peso_bruto is not None and pue_final)):
            if modo_preconteo:
                resultado = truncar_dos_decimales(cantidad_directa)
            else:
                tara_total = (0.045 if t_cont else 0) + (t_manual or 0.0)
                is_tinta = "TINTA" in str(art_sel).upper(); offset = 0.030 if is_tinta else 0.0
                resultado = truncar_dos_decimales((peso_bruto - tara_total - offset) / pue_final)
                formula = f"({peso_bruto:.3f}PB - {tara_total:.3f}T{' - 0.03Env' if is_tinta else ''}) / {pue_final}PUE"

            fh = datetime.now(zona_mx).strftime("%Y-%m-%d %H:%M:%S")
            try:
                with conn.session as s:
                    res_db = s.execute(text("""INSERT INTO pesajes_individuales (sucursal, fecha_hora, articulo, categoria, peso_bruto, tara, pue, resultado_pue, detalle_formula) 
                                 VALUES (:suc, :fh, :art, :cat, :pb, :tara, :pue, :rp, :df) RETURNING id"""),
                              {"suc": sucursal_in, "fh": fh, "art": art_sel, "cat": cat_reg, "pb": peso_bruto if not modo_preconteo else 0, "tara": tara_total if not modo_preconteo else 0, "pue": pue_final if not modo_preconteo else 0, "rp": resultado, "df": formula})
                    id_creado = res_db.fetchone()[0]
                    s.commit()
                mostrar_popup_exito(id_creado, art_sel, resultado, sucursal_in, cat_reg)
            except Exception as e: st.error(f"Error DB: {e}")
        else: st.error("❌ Revisa los datos de entrada.")

    if art_sel:
        st.divider()
        st.markdown(f"📋 **Historial de {art_sel}**")
        df_a = conn.query("SELECT * FROM pesajes_individuales WHERE articulo = :art AND sucursal = :suc", params={"art": art_sel, "suc": sucursal_in}, ttl=0)
        df_g = conn.query("SELECT * FROM pesajes_guardados WHERE articulo = :art AND sucursal = :suc", params={"art": art_sel, "suc": sucursal_in}, ttl=0)
        if not df_g.empty: df_g['detalle_formula'] = "[GUARDADO] " + df_g['detalle_formula'].astype(str)
        df_comb = pd.concat([df_a, df_g], ignore_index=True)
        if not df_comb.empty: st.dataframe(df_comb[['detalle_formula', 'resultado_pue']].rename(columns={'detalle_formula': 'Operación', 'resultado_pue': 'Cantidad'}), hide_index=True, use_container_width=True)

# --- TAB 2: EXPORTACIÓN Y BÓVEDA ---
with tab_historial:
    df_actual = conn.query("SELECT * FROM pesajes_individuales WHERE sucursal = :suc", params={"suc": sucursal_in}, ttl=0)
    df_guardados = conn.query("SELECT * FROM pesajes_guardados WHERE sucursal = :suc", params={"suc": sucursal_in}, ttl=0)

    if not df_actual.empty or not df_guardados.empty:
        if not df_guardados.empty:
            st.download_button("📄 Descargar Tarjetas en Word (Pre-conteos)", data=generar_word_tarjetas(df_guardados[['articulo', 'resultado_pue']].copy()), file_name=f"Tarjetas_{sucursal_in.replace(' ', '_')}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
            
        st.markdown(f'<a href="https://wa.me/{numero_wa}" target="_blank" class="btn-wa">💬 ABRIR WHATSAPP (Enviar archivos)</a>', unsafe_allow_html=True)
        st.divider()
        
        with st.expander("🗑️ Administración de Registros Individuales (Sesión Actual)", expanded=False):
            edited_df = st.data_editor(df_actual, use_container_width=True, num_rows="dynamic", hide_index=True, disabled=df_actual.columns.tolist(), key="ed_db")
            if st.button("💾 Guardar Cambios en Tabla"):
                ids_del = set(df_actual['id']) - set(edited_df['id'])
                if ids_del:
                    with conn.session as s:
                        for d_id in ids_del: s.execute(text("DELETE FROM pesajes_individuales WHERE id = :id"), {"id": int(d_id)})
                        s.commit()
                    st.session_state.show_toast = f"✅ {len(ids_del)} eliminados."
                    st.rerun()

        with st.expander("🛡️ Trasladar a Bóveda (Permanentes)", expanded=False):
            opc_prot = df_actual.apply(lambda x: f"ID {x['id']} | {x['articulo']} | {x['resultado_pue']} u.", axis=1).tolist()
            sel_prot = st.multiselect("Selecciona para bóveda:", opc_prot)
            if st.button("📥 Mover seleccionados a la Bóveda") and sel_prot:
                with conn.session as s:
                    for sel in sel_prot:
                        id_val = int(sel.split(" | ")[0].replace("ID ", ""))
                        s.execute(text("""INSERT INTO pesajes_guardados (sucursal, fecha_hora, articulo, categoria, peso_bruto, tara, pue, resultado_pue, detalle_formula) SELECT sucursal, fecha_hora, articulo, categoria, peso_bruto, tara, pue, resultado_pue, detalle_formula FROM pesajes_individuales WHERE id = :id"""), {"id": id_val})
                        s.execute(text("DELETE FROM pesajes_individuales WHERE id = :id"), {"id": id_val})
                    s.commit()
                st.session_state.show_toast = f"✅ Movidos {len(sel_prot)} a Bóveda."
                st.rerun()
            
            if not df_guardados.empty:
                st.markdown("#### 🗃️ Bóveda Actual")
                ed_guardados = st.data_editor(df_guardados, use_container_width=True, num_rows="dynamic", hide_index=True, disabled=df_guardados.columns.tolist(), key="ed_gb")
                if st.button("💾 Eliminar filas de la Bóveda"):
                    ids_del_g = set(df_guardados['id']) - set(ed_guardados['id'])
                    if ids_del_g:
                        with conn.session as s:
                            for d_id in ids_del_g: s.execute(text("DELETE FROM pesajes_guardados WHERE id = :id"), {"id": int(d_id)})
                            s.commit()
                        st.session_state.show_toast = f"✅ Eliminados {len(ids_del_g)} guardados."
                        st.rerun()
    else: st.info("No hay pesajes registrados.")

# --- TAB 3: ESQUEMA VISUAL GLOBAL ---
with tab_visual:
    st.subheader("🖼️ Esquema Visual Global de Insumos")
    df_actual_all_v = conn.query("SELECT articulo, categoria, SUM(resultado_pue) as total_pesado FROM pesajes_individuales WHERE sucursal = :suc GROUP BY articulo, categoria", params={"suc": sucursal_in}, ttl=0)
    df_auditoria_base_v = conn.query("SELECT articulo, categoria, stock FROM auditoria_stock WHERE sucursal = :suc", params={"suc": sucursal_in}, ttl=0)

    filas_visual = []
    for cat_nombre, prod_map in productos_por_categoria.items():
        for art_nombre in prod_map.keys():
            stk_row = df_auditoria_base_v[(df_auditoria_base_v['articulo'] == art_nombre) & (df_auditoria_base_v['categoria'] == cat_nombre)]
            stock_val = float(stk_row['stock'].values[0]) if not stk_row.empty else 0.0

            pes_row = df_actual_all_v[(df_actual_all_v['articulo'] == art_nombre) & (df_actual_all_v['categoria'] == cat_nombre)]
            pesado_val = float(pes_row['total_pesado'].values[0]) if not pes_row.empty else 0.0

            filas_visual.append({
                "Producto": art_nombre, "Categoría": cat_nombre, 
                "Cantidad Anterior": stock_val, "Peso Obtenido": pesado_val, "Stock Actual": stock_val - pesado_val
            })

    df_reporte_visual = pd.DataFrame(filas_visual)
    if not df_reporte_visual.empty:
        st.image(generar_imagen_esquema(df_reporte_visual, sucursal_in), use_container_width=True)
        st.markdown(f'<a href="https://wa.me/{numero_wa}" target="_blank" class="btn-wa">📞 Enviar Reporte a {sucursal_in}</a>', unsafe_allow_html=True)
    else: st.info("Faltan datos para el esquema visual.")

# --- AUTO-FOCO CON JAVASCRIPT ---
components.html("""
    <script>
    const num_inputs = window.parent.document.querySelectorAll('input[type="number"]');
    num_inputs.forEach(input => input.setAttribute('enterkeyhint', 'done'));
    setTimeout(() => {
        const selectores = window.parent.document.querySelectorAll('input[aria-autocomplete="list"], input[role="combobox"]');
        if(selectores.length > 0) selectores[0].focus();
    }, 600); 
    </script>
""", height=0)
